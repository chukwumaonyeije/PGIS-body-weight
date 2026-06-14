import { ApiError } from "@/lib/api";

type ErrorContext = "auth" | "intake" | "program" | "session" | "default";

const DEFAULT_MESSAGES: Record<ErrorContext, string> = {
  auth: "We could not sign you in. Check your email and password, then try again.",
  intake: "We could not save your intake right now. Please review your answers and try again.",
  program: "We could not load your program right now. Please refresh or create a new program.",
  session: "We could not load this session right now. Please go back to your program and try again.",
  default: "Something went wrong. Please try again.",
};

const VALIDATION_MESSAGE =
  "Some information needs another look. Please check the highlighted fields and try again.";

export function getFriendlyErrorMessage(
  error: unknown,
  context: ErrorContext = "default",
): string {
  if (error instanceof ApiError) {
    if (error.status === 401 || error.status === 403) {
      return "Your session has expired. Please sign in again.";
    }
    if (error.status === 409 && context === "auth") {
      return "An account already exists for that email. Try signing in instead.";
    }
    if (error.status === 422 || hasValidationDetail(error.detail)) {
      return VALIDATION_MESSAGE;
    }
    if (error.status >= 500) {
      return "The service is having trouble right now. Please try again in a moment.";
    }
    return DEFAULT_MESSAGES[context];
  }

  if (error instanceof TypeError) {
    return "We could not reach the server. Check your connection and try again.";
  }

  return DEFAULT_MESSAGES[context];
}

function hasValidationDetail(detail: unknown): boolean {
  return Array.isArray(detail) && detail.some(item => {
    return typeof item === "object" && item !== null && "loc" in item && "msg" in item;
  });
}
