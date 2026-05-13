import { createClient } from '@supabase/supabase-js'

/*
|--------------------------------------------------------------------------
| Supabase Client Configuration
|--------------------------------------------------------------------------
| These values are exposed safely to the browser through NEXT_PUBLIC variables.
| The service-role key must never be used in frontend code.
|--------------------------------------------------------------------------
*/

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL
const supabaseKey = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY

if (!supabaseUrl || !supabaseKey) {
  throw new Error('Missing Supabase environment variables')
}

export const supabase = createClient(supabaseUrl, supabaseKey)