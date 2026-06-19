import { z } from 'zod';

export const loginSchema = z.object({
  username: z
    .string()
    .trim()
    .min(1, { message: "L'identifiant est obligatoire." }),
  password: z
    .string()
    .min(4, { message: "Le mot de passe doit contenir au moins 4 caracteres." }),
});
