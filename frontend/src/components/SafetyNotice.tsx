interface SafetyNoticeProps {
  compact?: boolean;
}

export default function SafetyNotice({ compact = false }: SafetyNoticeProps) {
  return (
    <div className="rounded-lg border border-amber-200 bg-amber-50 px-4 py-3 text-xs leading-5 text-amber-900">
      <p className="font-medium">Health and privacy notice</p>
      <p className={compact ? "mt-1" : "mt-1.5"}>
        PGIS Body Weight supports exercise planning and is not medical care. Follow your clinician&apos;s
        guidance for diabetes, glucose monitoring, symptoms, fall risk, and exercise restrictions.
        Intake and glucose entries are health-sensitive; avoid entering information you do not want stored.
      </p>
    </div>
  );
}
