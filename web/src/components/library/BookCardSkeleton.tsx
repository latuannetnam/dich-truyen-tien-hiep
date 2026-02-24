export default function BookCardSkeleton() {
  return (
    <div className="bg-[var(--bg-surface)] border border-[var(--border-default)] rounded-xl p-6">
      {/* Title skeleton */}
      <div className="skeleton h-5 w-3/4 mb-2" />
      {/* Subtitle skeleton */}
      <div className="skeleton h-4 w-1/2 mb-1" />
      {/* Author skeleton */}
      <div className="skeleton h-3 w-1/3 mb-4" />
      {/* Progress bar skeleton */}
      <div className="skeleton h-1.5 w-full mb-2 rounded-full" />
      {/* Chapter count skeleton */}
      <div className="flex justify-between">
        <div className="skeleton h-3 w-24" />
        <div className="skeleton h-3 w-8" />
      </div>
    </div>
  );
}
