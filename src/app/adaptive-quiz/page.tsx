'use client'

import { useEffect, useState } from 'react'
import { getAdaptiveQuizData } from '../lib/api'

function shuffleArray<T>(array: T[]) {
  return [...array].sort(() => Math.random() - 0.5)
}

export default function AdaptiveQuizPage() {
  const [student, setStudent] = useState<any>(null)
  const [questions, setQuestions] = useState<any[]>([])
  const [answers, setAnswers] = useState<Record<string, string>>({})
  const [score, setScore] = useState<number | null>(null)
  const [submitted, setSubmitted] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    async function loadQuiz() {
      try {
        const data = await getAdaptiveQuizData()

        const shuffledQuestions = shuffleArray(data.questions).map(
          (question: any) => {
            const shuffledChoices = shuffleArray(
              [
                question.choice_1,
                question.choice_2,
                question.choice_3,
                question.correct_answer,
              ]
                .filter(Boolean)
                .filter(
                  (value, index, self) => self.indexOf(value) === index
                )
            )

            return {
              ...question,
              shuffledChoices,
            }
          }
        )

        setStudent(data.student)
        setQuestions(shuffledQuestions)
      } catch (error: any) {
        setError(error?.message || 'Failed to load adaptive quiz')
      } finally {
        setLoading(false)
      }
    }

    loadQuiz()
  }, [])

  function handleSelect(questionId: string, answer: string) {
    if (submitted) return

    setAnswers((prev) => ({
      ...prev,
      [questionId]: answer,
    }))
  }

  function handleSubmit() {
    let correctCount = 0

    questions.forEach((question) => {
      if (answers[question.id] === question.correct_answer) {
        correctCount += 1
      }
    })

    setScore(correctCount)
    setSubmitted(true)
  }

  function handleRetry() {
    const reshuffledQuestions = shuffleArray(questions).map((question: any) => {
      const reshuffledChoices = shuffleArray(question.shuffledChoices)

      return {
        ...question,
        shuffledChoices: reshuffledChoices,
      }
    })

    setQuestions(reshuffledQuestions)
    setAnswers({})
    setScore(null)
    setSubmitted(false)
  }

  if (loading) return <p>Loading adaptive quiz...</p>
  if (error) return <p>Error: {error}</p>

  const firstName = student?.display_name?.split(' ')[0] || 'Student'
  const allAnswered = questions.every((question) => answers[question.id])

  return (
    <div>
      <div className="page-heading">
        <h1>{firstName}&apos;s Adaptive Quiz</h1>
        <p>Questions tailored to your current weak areas.</p>
      </div>

      {questions.length === 0 ? (
        <div className="empty-state">
          <p>No adaptive quiz questions available yet.</p>
        </div>
      ) : (
        <>
          <div className="adaptive-quiz-list">
            {questions.map((question, index) => (
              <div className="adaptive-quiz-card" key={question.id}>
                <span className="quiz-area">{question.weak_area}</span>

                <h3>
                  Question {index + 1}: {question.question_text}
                </h3>

                <div className="quiz-options">
                  {question.shuffledChoices.map(
                    (choice: string, choiceIndex: number) => {
                      const selected = answers[question.id] === choice
                      const isCorrect = question.correct_answer === choice

                      const optionLabel = String.fromCharCode(65 + choiceIndex)

                      let className = 'quiz-option'

                      if (selected) className += ' selected'
                      if (submitted && isCorrect) className += ' correct'
                      if (submitted && selected && !isCorrect) {
                        className += ' incorrect'
                      }

                      return (
                        <button
                          type="button"
                          key={choice}
                          className={className}
                          onClick={() => handleSelect(question.id, choice)}
                        >
                          {optionLabel}. {choice}
                        </button>
                      )
                    }
                  )}
                </div>

                {submitted && question.explanation && (
                  <p className="quiz-explanation">
                    {question.explanation}
                  </p>
                )}
              </div>
            ))}
          </div>

          <div className="quiz-submit-row">
            {!submitted ? (
              <button
                type="button"
                className="quiz-submit-button"
                disabled={!allAnswered}
                onClick={handleSubmit}
              >
                Submit Answers
              </button>
            ) : (
              <div className="quiz-result-wrap">
                <div className="quiz-result">
                  Score: {score}/{questions.length}
                </div>

                <button
                  type="button"
                  className="quiz-retry-button"
                  onClick={handleRetry}
                >
                  Retry Quiz
                </button>
              </div>
            )}
          </div>
        </>
      )}
    </div>
  )
}