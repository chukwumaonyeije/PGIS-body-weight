"use client";

import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { z } from "zod";
import { useRouter } from "next/navigation";
import { submitIntake, generateProgram } from "@/lib/api";
import { getToken, getUserId } from "@/lib/auth";
import { cn } from "@/lib/utils";
import SafetyNotice from "@/components/SafetyNotice";

const schema = z.object({
  age: z.coerce.number().int().min(60).max(99),
  sex: z.enum(["male", "female", "non_binary"]),
  medication_class: z.enum([
    "none", "metformin_only", "insulin", "sulfonylurea", "meglitinide", "other",
  ]),
  parq_chest_pain: z.boolean(),
  parq_dizziness: z.boolean(),
  parq_cardiac: z.boolean(),
  parq_bone_joint: z.boolean(),
  fall_risk: z.boolean(),
  joint_knee: z.boolean(),
  joint_lower_back: z.boolean(),
  joint_hip: z.boolean(),
  joint_shoulder: z.boolean(),
  joint_wrist: z.boolean(),
  sit_to_stand_count: z.coerce.number().int().min(0).max(60),
  pushup_max: z.coerce.number().int().min(0).max(100),
  single_leg_stand_s: z.coerce.number().min(0).max(60),
  days_per_week: z.coerce.number().int().min(2).max(5),
  minutes_per_session: z.coerce.number().int().min(10).max(60),
});
type Fields = z.infer<typeof schema>;

const STEPS = ["About you", "Health history", "Fitness tests", "Schedule"];

export default function IntakePage() {
  const router = useRouter();
  const [step, setStep] = useState(0);
  const [error, setError] = useState<string | null>(null);

  const { register, handleSubmit, watch, formState: { errors, isSubmitting } } = useForm<Fields>({
    resolver: zodResolver(schema),
    defaultValues: {
      sex: "male",
      medication_class: "none",
      age: 60,
      days_per_week: 3,
      minutes_per_session: 20,
      parq_chest_pain: false,
      parq_dizziness: false,
      parq_cardiac: false,
      parq_bone_joint: false,
      fall_risk: false,
      joint_knee: false,
      joint_lower_back: false,
      joint_hip: false,
      joint_shoulder: false,
      joint_wrist: false,
      sit_to_stand_count: 10,
      pushup_max: 5,
      single_leg_stand_s: 10,
    },
  });

  const onSubmit = async (data: Fields) => {
    setError(null);
    const token = getToken();
    const userId = getUserId();
    if (!token || !userId) { router.push("/login"); return; }

    const parq_flags: string[] = [];
    if (data.parq_chest_pain) parq_flags.push("chest_pain_with_exertion");
    if (data.parq_dizziness)  parq_flags.push("uncontrolled_dizziness");
    if (data.parq_cardiac)    parq_flags.push("recent_cardiac_event");
    if (data.parq_bone_joint) parq_flags.push("bone_joint_condition");

    const joint_flags: string[] = [];
    if (data.joint_knee)        joint_flags.push("knee");
    if (data.joint_lower_back)  joint_flags.push("lower_back");
    if (data.joint_hip)         joint_flags.push("hip");
    if (data.joint_shoulder)    joint_flags.push("shoulder");
    if (data.joint_wrist)       joint_flags.push("wrist");

    try {
      const intakeRes = await submitIntake(userId, {
        age: data.age,
        sex: data.sex,
        parq_flags,
        medication_class: data.medication_class,
        joint_flags,
        functional_tests: {
          sit_to_stand_count: data.sit_to_stand_count,
          pushup_max: data.pushup_max,
          single_leg_stand_s: data.single_leg_stand_s,
        },
        days_per_week: data.days_per_week,
        minutes_per_session: data.minutes_per_session,
        fall_risk: data.fall_risk,
        equipment: [],
        goals: ["glucose_control"],
      }, token);

      if (intakeRes.clearance_required) {
        router.push(`/program?clearance=1&reason=${encodeURIComponent(intakeRes.clearance_reason ?? "")}`);
        return;
      }

      const programRes = await generateProgram(userId, intakeRes.intake_id, token);
      router.push(`/program?id=${programRes.program_id}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Something went wrong");
    }
  };

  const labelClass = "block text-sm font-medium text-gray-700 mb-1";
  const inputClass = (hasError?: boolean) => cn(
    "w-full px-3 py-2 border rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-brand-500",
    hasError ? "border-red-400" : "border-gray-300",
  );
  const checkClass = "h-4 w-4 text-brand-600 border-gray-300 rounded";

  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-white border-b px-6 py-4 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 bg-brand-600 rounded-md flex items-center justify-center">
            <span className="text-white font-bold text-sm">P</span>
          </div>
          <span className="font-semibold text-gray-900">PGIS Body Weight</span>
        </div>
        <span className="text-sm text-gray-500">Step {step + 1} of {STEPS.length}: {STEPS[step]}</span>
      </header>

      <div className="flex-1 flex items-center justify-center px-4 py-8">
        <div className="w-full max-w-lg bg-white rounded-2xl shadow-sm border p-8">
          <div className="mb-6">
            <SafetyNotice />
          </div>

          {/* Progress bar */}
          <div className="flex gap-2 mb-8">
            {STEPS.map((s, i) => (
              <div
                key={s}
                className={cn(
                  "flex-1 h-1 rounded-full transition-colors",
                  i <= step ? "bg-brand-500" : "bg-gray-200"
                )}
              />
            ))}
          </div>

          <form onSubmit={handleSubmit(onSubmit)}>

            {/* Step 0: About you */}
            {step === 0 && (
              <div className="space-y-5">
                <h2 className="text-xl font-semibold">About you</h2>

                <div>
                  <label className={labelClass}>Age</label>
                  <input type="number" {...register("age")} className={inputClass(!!errors.age)} />
                  {errors.age && <p className="text-xs text-red-500 mt-1">{errors.age.message}</p>}
                  <p className="text-xs text-gray-400 mt-1">Must be 60 or older</p>
                </div>

                <div>
                  <label className={labelClass}>Sex assigned at birth</label>
                  <select {...register("sex")} className={inputClass()}>
                    <option value="male">Male</option>
                    <option value="female">Female</option>
                    <option value="non_binary">Non-binary / prefer not to say</option>
                  </select>
                </div>

                <div>
                  <label className={labelClass}>Diabetes medication</label>
                  <select {...register("medication_class")} className={inputClass()}>
                    <option value="none">None</option>
                    <option value="metformin_only">Metformin only</option>
                    <option value="insulin">Insulin</option>
                    <option value="sulfonylurea">Sulfonylurea</option>
                    <option value="meglitinide">Meglitinide</option>
                    <option value="other">Other</option>
                  </select>
                </div>
              </div>
            )}

            {/* Step 1: Health history */}
            {step === 1 && (
              <div className="space-y-5">
                <h2 className="text-xl font-semibold">Health history</h2>
                <p className="text-sm text-gray-500">Check any that apply. A checked item routes you to physician clearance before training begins.</p>

                <div className="space-y-3">
                  {[
                    { name: "parq_chest_pain" as const, label: "Chest pain during exertion" },
                    { name: "parq_dizziness" as const, label: "Uncontrolled dizziness or balance problems" },
                    { name: "parq_cardiac" as const, label: "Recent cardiac event (heart attack, stent, surgery)" },
                    { name: "parq_bone_joint" as const, label: "Bone or joint condition worsened by exercise" },
                    { name: "fall_risk" as const, label: "Recent fall or physician-assessed fall risk" },
                  ].map(({ name, label }) => (
                    <label key={name} className="flex items-center gap-3 cursor-pointer">
                      <input type="checkbox" {...register(name)} className={checkClass} />
                      <span className="text-sm text-gray-700">{label}</span>
                    </label>
                  ))}
                </div>

                <div className="mt-4">
                  <p className="text-sm font-medium text-gray-700 mb-2">Joint pain or restriction (optional)</p>
                  <p className="text-xs text-gray-400 mb-3">Exercises will be modified to avoid these areas.</p>
                  <div className="space-y-3">
                    {[
                      { name: "joint_knee" as const, label: "Knee" },
                      { name: "joint_lower_back" as const, label: "Lower back" },
                      { name: "joint_hip" as const, label: "Hip" },
                      { name: "joint_shoulder" as const, label: "Shoulder" },
                      { name: "joint_wrist" as const, label: "Wrist" },
                    ].map(({ name, label }) => (
                      <label key={name} className="flex items-center gap-3 cursor-pointer">
                        <input type="checkbox" {...register(name)} className={checkClass} />
                        <span className="text-sm text-gray-700">{label}</span>
                      </label>
                    ))}
                  </div>
                </div>
              </div>
            )}

            {/* Step 2: Fitness tests */}
            {step === 2 && (
              <div className="space-y-5">
                <h2 className="text-xl font-semibold">Fitness tests</h2>
                <p className="text-sm text-gray-500">These three tests set your starting exercise level for each movement pattern.</p>

                <div>
                  <label className={labelClass}>30-second sit-to-stand (reps)</label>
                  <input type="number" {...register("sit_to_stand_count")} className={inputClass(!!errors.sit_to_stand_count)} />
                  <p className="text-xs text-gray-400 mt-1">From a standard chair, how many times can you stand and sit in 30 seconds?</p>
                  {errors.sit_to_stand_count && <p className="text-xs text-red-500 mt-1">{errors.sit_to_stand_count.message}</p>}
                </div>

                <div>
                  <label className={labelClass}>Pushup max (reps)</label>
                  <input type="number" {...register("pushup_max")} className={inputClass(!!errors.pushup_max)} />
                  <p className="text-xs text-gray-400 mt-1">Wall or floor pushups to fatigue. Enter 0 if unsure.</p>
                  {errors.pushup_max && <p className="text-xs text-red-500 mt-1">{errors.pushup_max.message}</p>}
                </div>

                <div>
                  <label className={labelClass}>Single-leg stand (seconds)</label>
                  <input type="number" step="0.5" {...register("single_leg_stand_s")} className={inputClass(!!errors.single_leg_stand_s)} />
                  <p className="text-xs text-gray-400 mt-1">Eyes open, hands on hips. How long can you balance on one leg?</p>
                  {errors.single_leg_stand_s && <p className="text-xs text-red-500 mt-1">{errors.single_leg_stand_s.message}</p>}
                </div>
              </div>
            )}

            {/* Step 3: Schedule */}
            {step === 3 && (
              <div className="space-y-5">
                <h2 className="text-xl font-semibold">Schedule</h2>

                <div>
                  <label className={labelClass}>Training days per week</label>
                  <select {...register("days_per_week")} className={inputClass()}>
                    <option value={2}>2 days</option>
                    <option value={3}>3 days</option>
                    <option value={4}>4 days</option>
                    <option value={5}>5 days</option>
                  </select>
                </div>

                <div>
                  <label className={labelClass}>Minutes per session</label>
                  <select {...register("minutes_per_session")} className={inputClass()}>
                    <option value={20}>20 minutes</option>
                    <option value={30}>30 minutes</option>
                    <option value={45}>45 minutes</option>
                    <option value={60}>60 minutes</option>
                  </select>
                </div>

                {error && (
                  <div className="bg-red-50 border border-red-200 text-red-700 text-sm px-3 py-2 rounded-lg">
                    {error}
                  </div>
                )}
              </div>
            )}

            {/* Navigation */}
            <div className="flex justify-between mt-8">
              {step > 0 ? (
                <button
                  type="button"
                  onClick={() => setStep(s => s - 1)}
                  className="px-4 py-2 text-sm font-medium text-gray-600 hover:text-gray-900"
                >
                  Back
                </button>
              ) : <div />}

              {step < STEPS.length - 1 ? (
                <button
                  type="button"
                  onClick={() => setStep(s => s + 1)}
                  className="bg-brand-600 hover:bg-brand-700 text-white text-sm font-medium px-5 py-2 rounded-lg"
                >
                  Next
                </button>
              ) : (
                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="bg-brand-600 hover:bg-brand-700 disabled:opacity-60 text-white text-sm font-medium px-5 py-2 rounded-lg"
                >
                  {isSubmitting ? "Generating..." : "Generate my program"}
                </button>
              )}
            </div>
          </form>
        </div>
      </div>
    </div>
  );
}
