export default function AdaptiveQuizPage() {
  return (
    <div>
      <div className="page-heading">
        <h1>Adaptive Quiz</h1>
        <p>Questions tailored to weak areas will appear here once learning data is available.</p>
      </div>

      <div className="empty-state">
        <p>No quiz generated yet</p>
      </div>
    </div>
  )
}