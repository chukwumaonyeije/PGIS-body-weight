"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { getToken, getUserId } from "@/lib/auth";
import { getProgram, getCoaching, type Session, type ExerciseInstance } from "@/lib/api";
import { getFriendlyErrorMessage } from "@/lib/errors";
import ErrorMessage from "@/components/ErrorMessage";
import SafetyNotice from "@/components/SafetyNotice";

function ExerciseCard({ ex }: { ex: ExerciseInstance }) {
  const [showAlts, setShowAlts] = useState(false);
  return (
    <div className="bg-white border rounded-xl p-4">
      <div className="flex items-start justify-between">
        <div>
          <h3 className="font-medium text-gray-900 capitalize">
            {ex.exercise_id.replace(/_/g, " ")}
          </h3>
          <p className="text-sm text-gray-600 mt-0.5">
            {ex.sets} sets · {ex.reps_or_time} · RPE {ex.target_rpe}
          </p>
          {ex.rest_s > 0 && (
            <p className="text-xs text-gray-400 mt-0.5">{ex.rest_s}s rest</p>
          )}
        </div>
        <button
          onClick={() => setShowAlts(v => !v)}
          className="text-xs text-brand-600 hover:underline ml-4 shrink-0"
        >
          {showAlts ? "Hide" : "Alts"}
        </button>
      </div>
      {showAlts && (
        <div className="mt-3 pt-3 border-t space-y-1 text-xs text-gray-500">
          <p><span className="font-medium text-gray-700">Easier:</span> {ex.regression_alt.replace(/_/g, " ")}</p>
          <p><span className="font-medium text-gray-700">Harder:</span> {ex.progression_alt.replace(/_/g, " ")}</p>
        </div>
      )}
    </div>
  );
}

function SessionPageContent() {
  const router = useRouter();
  const params = useSearchParams();
  const programId = params.get("pid");
  const week = Number(params.get("w"));
  const day = Number(params.get("d"));

  const [session, setSession] = useState<Session | null>(null);
  const [coaching, setCoaching] = useState<string | null>(null);
  const [loadingCoaching, setLoadingCoaching] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = getToken();
    const userId = getUserId();
    if (!token || !userId) { router.push("/login"); return; }
    if (!programId || !week || !day) { router.push("/program"); return; }

    getProgram(programId, userId, token)
      .then(res => {
        if (!res.program) return;
        const s = res.program.weeks
          .find(w => w.week_number === week)
          ?.sessions.find(s => s.day === day);
        setSession(s ?? null);
      })
      .catch(err => setError(getFriendlyErrorMessage(err, "session")));

    setLoadingCoaching(true);
    getCoaching(programId, week, day, userId, token)
      .then(res => setCoaching(res.coaching_text))
      .catch(() => setCoaching(null))
      .finally(() => setLoadingCoaching(false));
  }, [programId, week, day, router]);

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <ErrorMessage message={error} />
      </div>
    );
  }

  const blocks = session?.blocks ?? [];
  const warmup   = blocks.find(b => b.name === "warmup");
  const main     = blocks.find(b => b.name === "main");
  const cooldown = blocks.find(b => b.name === "cooldown");

  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-white border-b px-6 py-4 flex items-center gap-4 sticky top-0 z-10">
        <Link href={`/program?id=${programId}`} className="text-gray-500 hover:text-gray-900 text-sm">
          ← Back
        </Link>
        <span className="font-semibold text-gray-900">
          Week {week}, Day {day}
        </span>
        {session?.glucose_check_required && (
          <span className="text-xs bg-amber-100 text-amber-700 rounded-full px-3 py-1">
            Check glucose before starting
          </span>
        )}
      </header>

      <main className="flex-1 max-w-2xl mx-auto w-full px-4 py-8 space-y-8">

        {/* Coaching */}
        <div className="bg-brand-50 border border-brand-100 rounded-xl p-5">
          <h2 className="text-sm font-semibold text-brand-700 uppercase tracking-wide mb-2">
            Session coaching
          </h2>
          {loadingCoaching ? (
            <p className="text-sm text-gray-400 italic">Loading coaching notes...</p>
          ) : coaching ? (
            <p className="text-sm text-gray-700 whitespace-pre-line">{coaching}</p>
          ) : (
            <p className="text-sm text-gray-400 italic">Coaching unavailable for this session.</p>
          )}
        </div>

        {/* Warmup */}
        {warmup && (
          <section>
            <h2 className="text-xs font-semibold uppercase tracking-wide text-gray-400 mb-3">
              Warm-up
            </h2>
            <div className="space-y-2">
              {warmup.exercises.map(ex => <ExerciseCard key={ex.exercise_id} ex={ex} />)}
            </div>
          </section>
        )}

        {/* Main block */}
        {main && (
          <section>
            <h2 className="text-xs font-semibold uppercase tracking-wide text-gray-400 mb-3">
              Main
            </h2>
            <div className="space-y-2">
              {main.exercises.map(ex => <ExerciseCard key={ex.exercise_id} ex={ex} />)}
            </div>
          </section>
        )}

        {/* Cooldown */}
        {cooldown && (
          <section>
            <h2 className="text-xs font-semibold uppercase tracking-wide text-gray-400 mb-3">
              Cool-down
            </h2>
            <div className="space-y-2">
              {cooldown.exercises.map(ex => <ExerciseCard key={ex.exercise_id} ex={ex} />)}
            </div>
          </section>
        )}

        {!session && (
          <p className="text-gray-400 text-sm text-center py-8">Loading session...</p>
        )}

        <SafetyNotice compact />
      </main>
    </div>
  );
}

export default function SessionPage() {
  return (
    <Suspense fallback={null}>
      <SessionPageContent />
    </Suspense>
  );
}
