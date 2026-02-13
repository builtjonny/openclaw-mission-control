import { useMemo, useState } from "react";

import { ApiError } from "@/api/mutator";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";

export type SkillFormValues = {
  name: string;
  slug: string;
  summary: string;
  instructions: string;
  category: string;
};

type SkillFormProps = {
  initialValues?: SkillFormValues;
  onSubmit: (values: {
    name: string;
    slug: string | null;
    summary: string | null;
    instructions: string | null;
    category: string | null;
  }) => Promise<void>;
  onCancel: () => void;
  submitLabel: string;
  submittingLabel: string;
  isSubmitting: boolean;
};

const DEFAULT_VALUES: SkillFormValues = {
  name: "",
  slug: "",
  summary: "",
  instructions: "",
  category: "",
};

const slugify = (value: string) =>
  value
    .toLowerCase()
    .trim()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");

const extractErrorMessage = (error: unknown, fallback: string) => {
  if (error instanceof ApiError) return error.message || fallback;
  if (error instanceof Error) return error.message || fallback;
  return fallback;
};

export function SkillForm({
  initialValues,
  onSubmit,
  onCancel,
  submitLabel,
  submittingLabel,
  isSubmitting,
}: SkillFormProps) {
  const resolvedInitial = initialValues ?? DEFAULT_VALUES;
  const [name, setName] = useState(() => resolvedInitial.name);
  const [slug, setSlug] = useState(() => resolvedInitial.slug);
  const [summary, setSummary] = useState(() => resolvedInitial.summary);
  const [instructions, setInstructions] = useState(
    () => resolvedInitial.instructions,
  );
  const [category, setCategory] = useState(() => resolvedInitial.category);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);

  const suggestedSlug = useMemo(() => slugify(name.trim()), [name]);

  const handleSubmit = async (event: React.FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const normalizedName = name.trim();
    if (!normalizedName) {
      setErrorMessage("Skill name is required.");
      return;
    }
    setErrorMessage(null);
    try {
      await onSubmit({
        name: normalizedName,
        slug: slug.trim() || null,
        summary: summary.trim() || null,
        instructions: instructions.trim() || null,
        category: category.trim() || null,
      });
    } catch (error) {
      setErrorMessage(extractErrorMessage(error, "Unable to save skill."));
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      className="space-y-6 rounded-xl border border-slate-200 bg-white p-6 shadow-sm"
    >
      <div className="space-y-5">
        <div className="rounded-xl border border-slate-200 bg-slate-50/40 p-4">
          <div className="grid gap-4 md:grid-cols-2">
            <div className="space-y-2">
              <label className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                Name
              </label>
              <Input
                value={name}
                onChange={(event) => setName(event.target.value)}
                placeholder="e.g. Daily Briefing"
                disabled={isSubmitting}
              />
            </div>
            <div className="space-y-2">
              <div className="flex items-center justify-between gap-2">
                <label className="text-xs font-semibold uppercase tracking-wider text-slate-500">
                  Slug
                </label>
                <button
                  type="button"
                  onClick={() => setSlug(suggestedSlug)}
                  className="text-xs font-medium text-slate-500 underline underline-offset-2 transition hover:text-slate-700 disabled:cursor-not-allowed disabled:opacity-50"
                  disabled={!suggestedSlug || isSubmitting}
                >
                  Use from name
                </button>
              </div>
              <Input
                value={slug}
                onChange={(event) => setSlug(event.target.value)}
                placeholder="daily-briefing"
                disabled={isSubmitting}
              />
            </div>
          </div>
          <p className="mt-2 text-xs text-slate-500">
            Leave slug blank to auto-generate from the skill name.
          </p>
        </div>

        <div className="grid gap-4 md:grid-cols-2">
          <div className="space-y-2">
            <label className="text-xs font-semibold uppercase tracking-wider text-slate-500">
              Category
            </label>
            <Input
              value={category}
              onChange={(event) => setCategory(event.target.value)}
              placeholder="e.g. Productivity"
              disabled={isSubmitting}
            />
          </div>
          <div className="space-y-2">
            <label className="text-xs font-semibold uppercase tracking-wider text-slate-500">
              Summary
            </label>
            <Input
              value={summary}
              onChange={(event) => setSummary(event.target.value)}
              placeholder="Short description of the skill"
              disabled={isSubmitting}
            />
          </div>
        </div>

        <div className="space-y-2">
          <label className="text-xs font-semibold uppercase tracking-wider text-slate-500">
            Instructions (SKILL.md content)
          </label>
          <Textarea
            value={instructions}
            onChange={(event) => setInstructions(event.target.value)}
            placeholder="Markdown instructions for agents using this skill..."
            className="min-h-[200px] font-mono text-sm"
            disabled={isSubmitting}
          />
          <p className="text-xs text-slate-500">
            These instructions are delivered to agents as a SKILL_*.md file in
            their workspace.
          </p>
        </div>

        {errorMessage ? (
          <div className="rounded-lg border border-rose-200 bg-rose-50 p-3 text-sm text-rose-700">
            {errorMessage}
          </div>
        ) : null}
      </div>

      <div className="flex justify-end gap-3">
        <Button
          type="button"
          variant="outline"
          onClick={onCancel}
          disabled={isSubmitting}
        >
          Cancel
        </Button>
        <Button type="submit" disabled={isSubmitting}>
          {isSubmitting ? submittingLabel : submitLabel}
        </Button>
      </div>
    </form>
  );
}
