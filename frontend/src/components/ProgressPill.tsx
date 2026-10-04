interface ProgressPillProps {
  stage: string;
}

export default function ProgressPill({ stage }: ProgressPillProps) {
  return (
    <section aria-label="Generation progress" className="mt-7">
      <p
        role="status"
        className="inline-flex items-center gap-2.5 rounded-full border border-pine bg-white px-3.5 py-1.5 text-[13px] font-semibold text-pine shadow-sm dark:border-sage/30 dark:bg-sage/[0.08] dark:text-sage dark:shadow-[0_0_24px_rgba(143,208,174,0.15)]"
      >
        <span
          aria-hidden="true"
          className="inline-block h-4 w-4 rounded-full border-2 border-line border-t-pine motion-safe:animate-spin dark:border-t-sage"
        />
        {stage}…
      </p>
    </section>
  );
}
