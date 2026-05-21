'use client'

import { useEffect, useState } from 'react'
import { getAdaptiveQuizData } from '../lib/api'

interface QuizQuestion {
  id: string
  learning_report_id: string
  course_name: string
  weak_area: string
  question_number: number
  question_text: string
  choice_1: string
  choice_2: string
  choice_3: string
  correct_answer: string
  explanation: string
  shuffled_choices?: string[]
}

function shuffleArray<T>(array: T[]) {
  return [...array].sort(() => Math.random() - 0.5)
}

export default function AdaptiveQuizPage() {
  const [questions, setQuestions] = useState<QuizQuestion[]>([])
  const [studentName, setStudentName] = useState('Student')
  const [selectedAnswers, setSelectedAnswers] = useState<Record<string, string>>(
    {}
  )
  const [submitted, setSubmitted] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    async function loadQuizData() {
      try {
        setLoading(true)

        const data = await getAdaptiveQuizData()

        const shuffledQuestions = shuffleArray(
          data.questions ?? []
        ).map((question: QuizQuestion) => ({
          ...question,
          shuffled_choices: shuffleArray([
            question.choice_1,
            question.choice_2,
            question.choice_3,
          ]),
        }))

        setQuestions(shuffledQuestions)
        setStudentName(data.student?.display_name ?? 'Student')
      } catch (err: any) {
        console.error(err)
        setError(err.message || 'Failed to load adaptive quiz')
      } finally {
        setLoading(false)
      }
    }

    loadQuizData()
  }, [])

  function handleAnswer(questionId: string, answer: string) {
    if (submitted) return

    setSelectedAnswers((current) => ({
      ...current,
      [questionId]: answer,
    }))
  }

  function getScore() {
    return questions.filter(
      (question) => selectedAnswers[question.id] === question.correct_answer
    ).length
  }

  function retryQuiz() {
    const reshuffledQuestions = shuffleArray(questions).map((question) => ({
      ...question,
      shuffled_choices: shuffleArray([
        question.choice_1,
        question.choice_2,
        question.choice_3,
      ]),
    }))

    setQuestions(reshuffledQuestions)
    setSelectedAnswers({})
    setSubmitted(false)
  }

  if (loading) {
    return (
      <div className="page-heading">
        <h1>Adaptive Quiz</h1>
        <p>Loading quiz questions...</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="page-heading">
        <h1>Adaptive Quiz</h1>
        <p>{error}</p>
      </div>
    )
  }

  return (
    <div>
      <div className="page-heading">
        <h1>{studentName}&apos;s Adaptive Quiz</h1>
        <p>Questions tailored to your current weak areas.</p>
      </div>

      {questions.length === 0 ? (
        <div className="empty-state">
          <p>No adaptive quiz questions available yet.</p>
        </div>
      ) : (
        <>
          <div className="adaptive-quiz-list">
            {questions.map((question, index) => {
              const choices = question.shuffled_choices ?? [
                question.choice_1,
                question.choice_2,
                question.choice_3,
              ]

              return (
                <div
                  className="adaptive-quiz-card"
                  key={`${question.learning_report_id}-${question.id}-${index}`}
                >
                  {question.course_name && (
                    <p className="quiz-course">
                      {question.course_name}
                    </p>
                  )}

                  {question.weak_area && (
                    <p className="quiz-area">
                      {question.weak_area}
                    </p>
                  )}

                  <h3>
                    Question {index + 1}: {question.question_text}
                  </h3>

                  <div className="quiz-options">
                    {choices.map((choice, choiceIndex) => {
                      const isSelected =
                        selectedAnswers[question.id] === choice

                      const isCorrect =
                        submitted && choice === question.correct_answer

                      const isIncorrect =
                        submitted &&
                        isSelected &&
                        choice !== question.correct_answer

                      return (
                        <button
                          key={`${question.id}-${choiceIndex}`}
                          type="button"
                          className={[
                            'quiz-option',
                            isSelected ? 'selected' : '',
                            isCorrect ? 'correct' : '',
                            isIncorrect ? 'incorrect' : '',
                          ]
                            .filter(Boolean)
                            .join(' ')}
                          onClick={() => handleAnswer(question.id, choice)}
                        >
                          {String.fromCharCode(65 + choiceIndex)}. {choice}
                        </button>
                      )
                    })}
                  </div>

                  {submitted && question.explanation && (
                    <p className="quiz-explanation">
                      {question.explanation}
                    </p>
                  )}
                </div>
              )
            })}
          </div>

          <div className="quiz-submit-row">
            {!submitted ? (
              <button
                type="button"
                className="quiz-submit-button"
                onClick={() => setSubmitted(true)}
              >
                Submit Quiz
              </button>
            ) : (
              <div className="quiz-result-wrap">
                <p className="quiz-result">
                  Score: {getScore()} / {questions.length}
                </p>

                <button
                  type="button"
                  className="quiz-retry-button"
                  onClick={retryQuiz}
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