"use client";

import { type FormEvent, Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { getToken, getUserId } from "@/lib/auth";
import {
  getCoaching,
  getProgram,
  logGlucose,
  logSession,
  type ExerciseInstance,
  type Session,
} from "@/lib/api";
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
  const [completed, setCompleted] = useState<"yes" | "no">("yes");
  const [rpe, setRpe] = useState("6");
  const [notes, setNotes] = useState("");
  const [glucoseValue, setGlucoseValue] = useState("");
  const [logging, setLogging] = useState(false);
  const [logSuccess, setLogSuccess] = useState(false);
  const [logError, setLogError] = useState<string | null>(null);

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

  const handleCompletionSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setLogError(null);

    const token = getToken();
    const userId = getUserId();
    if (!token || !userId) { router.push("/login"); return; }
    if (!programId) { router.push("/program"); return; }
    if (!week || !day) { router.push("/program"); return; }

    if (completed === "no") {
      setLogError("Only completed sessions are logged for progress. Add notes here, then log when you finish.");
      return;
    }

    const parsedRpe = Number(rpe);
    if (!Number.isFinite(parsedRpe) || parsedRpe < 1 || parsedRpe > 10) {
      setLogError("Enter an RPE from 1 to 10.");
      return;
    }

    const parsedGlucose = glucoseValue ? Number(glucoseValue) : null;
    if (parsedGlucose !== null && (!Number.isFinite(parsedGlucose) || parsedGlucose <= 0)) {
      setLogError("Enter a glucose value greater than 0, or leave it blank.");
      return;
    }

    setLogging(true);
    try {
      const logged = await logSession(programId, {
        user_id: userId,
        week,
        day_in_week: day,
        per_exercise_rpe: { overall: parsedRpe },
        notes: notes.trim() || null,
      }, token);

      if (parsedGlucose !== null) {
        await logGlucose(
          userId,
          parsedGlucose,
          token,
          logged.log_id,
          notes.trim() || null,
        );
      }

      setLogSuccess(true);
    } catch (err) {
      setLogError(getFriendlyErrorMessage(err, "session"));
    } finally {
      setLogging(false);
    }
  };

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

        <section className="bg-white border rounded-xl p-5">
          {logSuccess ? (
            <div className="space-y-4">
              <div>
                <h2 className="text-lg font-semibold text-gray-900">Session logged</h2>
                <p className="text-sm text-gray-600 mt-1">
                  Your progress dashboard has been updated.
                </p>
              </div>
              <Link
                href={`/program?id=${programId}`}
                className="inline-flex items-center justify-center bg-brand-600 hover:bg-brand-700 text-white text-sm font-medium px-4 py-2 rounded-lg"
              >
                Back to program
              </Link>
            </div>
          ) : (
            <form onSubmit={handleCompletionSubmit} className="space-y-5">
              <div>
                <h2 className="text-lg font-semibold text-gray-900">Complete session</h2>
                <p className="text-sm text-gray-500 mt-1">
                  Log the session once you have finished training.
                </p>
              </div>

              <fieldset>
                <legend className="text-sm font-medium text-gray-700 mb-2">Completed?</legend>
                <div className="grid grid-cols-2 gap-2">
                  {(["yes", "no"] as const).map(value => (
                    <label
                      key={value}
                      className={`border rounded-lg px-3 py-2 text-sm cursor-pointer ${
                        completed === value ? "border-brand-500 bg-brand-50 text-brand-700" : "border-gray-200 text-gray-600"
                      }`}
                    >
                      <input
                        type="radio"
                        name="completed"
                        value={value}
                        checked={completed === value}
                        onChange={() => setCompleted(value)}
                        className="sr-only"
                      />
                      {value === "yes" ? "Yes" : "No"}
                    </label>
                  ))}
                </div>
              </fieldset>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1" htmlFor="rpe">
                  RPE
                </label>
                <input
                  id="rpe"
                  type="number"
                  min="1"
                  max="10"
                  step="0.5"
                  value={rpe}
                  onChange={event => setRpe(event.target.value)}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-200"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1" htmlFor="glucose">
                  Glucose value, optional
                </label>
                <input
                  id="glucose"
                  type="number"
                  min="1"
                  step="1"
                  inputMode="numeric"
                  value={glucoseValue}
                  onChange={event => setGlucoseValue(event.target.value)}
                  placeholder="mg/dL"
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-200"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1" htmlFor="notes">
                  Notes
                </label>
                <textarea
                  id="notes"
                  value={notes}
                  onChange={event => setNotes(event.target.value)}
                  rows={4}
                  className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-200"
                  placeholder="How did the session feel?"
                />
              </div>

              {logError && <ErrorMessage message={logError} className="px-4 py-3" />}

              <button
                type="submit"
                disabled={logging}
                className="w-full bg-brand-600 hover:bg-brand-700 disabled:bg-gray-300 text-white text-sm font-medium px-4 py-2 rounded-lg"
              >
                {logging ? "Logging..." : "Log session"}
              </button>
            </form>
          )}
        </section>
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
