"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useRouter } from "next/navigation";
import Link from "next/link";
import { login, register } from "@/lib/api";
import { saveAuth } from "@/lib/auth";
import { cn } from "@/lib/utils";
import { getFriendlyErrorMessage } from "@/lib/errors";
import ErrorMessage from "@/components/ErrorMessage";
import SafetyNotice from "@/components/SafetyNotice";

const schema = z.object({
  email: z.string().email("Enter a valid email"),
  password: z.string().min(8, "Password must be at least 8 characters"),
});
type Fields = z.infer<typeof schema>;

interface Props {
  mode: "login" | "register";
}

export default function AuthForm({ mode }: Props) {
  const router = useRouter();
  const [error, setError] = useState<string | null>(null);
  const { register: field, handleSubmit, formState: { errors, isSubmitting } } = useForm<Fields>({
    resolver: zodResolver(schema),
  });

  const onSubmit = async (data: Fields) => {
    setError(null);
    try {
      const res = mode === "register"
        ? await register(data.email, data.password)
        : await login(data.email, data.password);
      saveAuth(res.token, res.user_id);
      router.push("/program");
    } catch (err) {
      setError(getFriendlyErrorMessage(err, "auth"));
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center px-4">
      <div className="w-full max-w-sm">
        <div className="mb-8 text-center">
          <div className="w-10 h-10 bg-brand-600 rounded-lg mx-auto mb-4 flex items-center justify-center">
            <span className="text-white font-bold text-lg">P</span>
          </div>
          <h1 className="text-2xl font-semibold text-gray-900">PGIS Body Weight</h1>
          <p className="text-sm text-gray-500 mt-1">
            {mode === "login" ? "Sign in to your account" : "Create your account"}
          </p>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Email</label>
            <input
              {...field("email")}
              type="email"
              autoComplete="email"
              className={cn(
                "w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-500",
                errors.email ? "border-red-400" : "border-gray-300"
              )}
              placeholder="you@example.com"
            />
            {errors.email && <p className="text-xs text-red-500 mt-1">{errors.email.message}</p>}
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">Password</label>
            <input
              {...field("password")}
              type="password"
              autoComplete={mode === "login" ? "current-password" : "new-password"}
              className={cn(
                "w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-500",
                errors.password ? "border-red-400" : "border-gray-300"
              )}
              placeholder="••••••••"
            />
            {errors.password && <p className="text-xs text-red-500 mt-1">{errors.password.message}</p>}
          </div>

          {error && (
            <ErrorMessage message={error} />
          )}

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-full bg-brand-600 hover:bg-brand-700 disabled:opacity-60 text-white font-medium py-2 px-4 rounded-lg text-sm transition-colors"
          >
            {isSubmitting ? "Please wait..." : mode === "login" ? "Sign in" : "Create account"}
          </button>
        </form>

        <p className="text-center text-sm text-gray-500 mt-6">
          {mode === "login" ? (
            <>No account? <Link href="/register" className="text-brand-600 hover:underline">Register</Link></>
          ) : (
            <>Have an account? <Link href="/login" className="text-brand-600 hover:underline">Sign in</Link></>
          )}
        </p>

        <div className="mt-6">
          <SafetyNotice compact />
        </div>
      </div>
    </div>
  );
}
