"use client";

import { Suspense, useEffect, useState } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { getToken, getUserId, clearAuth } from "@/lib/auth";
import { getProgram, type Program } from "@/lib/api";
import { cn } from "@/lib/utils";
import SafetyNotice from "@/components/SafetyNotice";

function ExerciseBadge({ id }: { id: string }) {
  return (
    <span className="inline-block text-xs bg-gray-100 text-gray-700 rounded px-2 py-0.5">
      {id.replace(/_/g, " ")}
    </span>
  );
}

function ProgramPageContent() {
  const router = useRouter();
  const params = useSearchParams();
  const programId = params.get("id");
  const clearanceRequired = params.get("clearance") === "1";
  const clearanceReason = params.get("reason");

  const [program, setProgram] = useState<Program | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [openWeek, setOpenWeek] = useState<number>(1);

  useEffect(() => {
    const token = getToken();
    const userId = getUserId();
    if (!token || !userId) { router.push("/login"); return; }
    if (!programId) return;

    setLoading(true);
    getProgram(programId, userId, token)
      .then(res => setProgram(res.program))
      .catch(err => setError(err instanceof Error ? err.message : "Failed to load program"))
      .finally(() => setLoading(false));
  }, [programId, router]);

  const handleLogout = () => {
    clearAuth();
    router.push("/login");
  };

  if (clearanceRequired) {
    return (
      <div className="min-h-screen flex items-center justify-center px-4">
        <div className="max-w-md text-center">
          <div className="w-16 h-16 bg-amber-100 rounded-full flex items-center justify-center mx-auto mb-4">
            <span className="text-2xl">⚕️</span>
          </div>
          <h1 className="text-xl font-semibold mb-2">Physician clearance required</h1>
          <p className="text-gray-600 text-sm mb-4">
            {clearanceReason || "Based on your health history, please get clearance from your doctor before starting this program."}
          </p>
          <Link href="/intake" className="text-brand-600 hover:underline text-sm">
            Update my intake
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-white border-b px-6 py-4 flex items-center justify-between sticky top-0 z-10">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 bg-brand-600 rounded-md flex items-center justify-center">
            <span className="text-white font-bold text-sm">P</span>
          </div>
          <span className="font-semibold text-gray-900">PGIS Body Weight</span>
        </div>
        <div className="flex items-center gap-4">
          <Link href="/intake" className="text-sm text-brand-600 hover:underline">
            New program
          </Link>
          <button onClick={handleLogout} className="text-sm text-gray-500 hover:text-gray-900">
            Sign out
          </button>
        </div>
      </header>

      <main className="flex-1 max-w-3xl mx-auto w-full px-4 py-8">
        {!programId && !loading && (
          <div className="text-center py-16">
            <p className="text-gray-500 mb-4">No program yet.</p>
            <Link
              href="/intake"
              className="bg-brand-600 hover:bg-brand-700 text-white text-sm font-medium px-5 py-2 rounded-lg"
            >
              Create my program
            </Link>
          </div>
        )}

        {loading && (
          <div className="text-center py-16 text-gray-400 text-sm">Loading program...</div>
        )}

        {error && (
          <div className="bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-3 rounded-lg">
            {error}
          </div>
        )}

        {program && (
          <>
            <div className="mb-6 flex items-center justify-between">
              <div>
                <h1 className="text-2xl font-semibold">Your 4-week program</h1>
                <p className="text-sm text-gray-500 mt-1">
                  Engine {program.engine_version} · {program.hypo_risk === "elevated" ? "Pre-session glucose check required" : "Standard hypo risk"}
                </p>
              </div>
            </div>

            <div className="space-y-4">
              {program.weeks.map(week => (
                <div key={week.week_number} className="bg-white rounded-xl border overflow-hidden">
                  <button
                    className="w-full flex items-center justify-between px-5 py-4 text-left hover:bg-gray-50"
                    onClick={() => setOpenWeek(openWeek === week.week_number ? 0 : week.week_number)}
                  >
                    <div className="flex items-center gap-3">
                      <span className="font-semibold text-gray-900">
                        Week {week.week_number}
                      </span>
                      {week.is_deload && (
                        <span className="text-xs bg-blue-100 text-blue-700 rounded-full px-2 py-0.5">Deload</span>
                      )}
                    </div>
                    <span className="text-gray-400 text-sm">{openWeek === week.week_number ? "▲" : "▼"}</span>
                  </button>

                  {openWeek === week.week_number && (
                    <div className="border-t divide-y">
                      {week.sessions.map(session => (
                        <div key={`${session.week}-${session.day}`} className="px-5 py-4">
                          <div className="flex items-center justify-between mb-3">
                            <h3 className="font-medium text-gray-900">
                              Day {session.day}
                              {session.glucose_check_required && (
                                <span className="ml-2 text-xs bg-amber-100 text-amber-700 rounded-full px-2 py-0.5">
                                  Check glucose first
                                </span>
                              )}
                            </h3>
                            {programId && (
                              <Link
                                href={`/program/session?pid=${programId}&w=${session.week}&d=${session.day}`}
                                className="text-xs text-brand-600 hover:underline"
                              >
                                View session
                              </Link>
                            )}
                          </div>

                          {session.blocks
                            .filter(b => b.name === "main")
                            .map(block => (
                              <div key={block.name} className="flex flex-wrap gap-1.5">
                                {block.exercises.map(ex => (
                                  <ExerciseBadge key={ex.exercise_id} id={ex.exercise_id} />
                                ))}
                              </div>
                            ))}
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>

            <div className="mt-8">
              <SafetyNotice compact />
            </div>
          </>
        )}
      </main>
    </div>
  );
}

export default function ProgramPage() {
  return (
    <Suspense fallback={null}>
      <ProgramPageContent />
    </Suspense>
  );
}
