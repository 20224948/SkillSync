export async function getStudentData() {
  const res = await fetch('/api/test')

  if (!res.ok) {
    throw new Error('Failed to fetch student data')
  }

  return res.json()
}