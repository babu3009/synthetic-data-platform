import { useMutation } from '@tanstack/react-query'
import { validateRules } from '../services/validation'

export function useValidate() {
  return useMutation({
    mutationFn: (body: unknown) => validateRules(body),
  })
}
