"use client";

export const dynamic = "force-dynamic";

import { useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";

import { useAuth } from "@/auth/clerk";
import { useQueryClient } from "@tanstack/react-query";

import { ApiError } from "@/api/mutator";
import {
  getListSkillsApiV1SkillsGetQueryKey,
  type listSkillsApiV1SkillsGetResponse,
  useDeleteSkillApiV1SkillsSkillIdDelete,
  useListSkillsApiV1SkillsGet,
} from "@/api/generated/skills/skills";
import type { SkillRead } from "@/api/generated/model";
import { SkillsTable } from "@/components/skills/SkillsTable";
import { DashboardPageLayout } from "@/components/templates/DashboardPageLayout";
import { buttonVariants } from "@/components/ui/button";
import { ConfirmActionDialog } from "@/components/ui/confirm-action-dialog";
import { useOrganizationMembership } from "@/lib/use-organization-membership";
import { useUrlSorting } from "@/lib/use-url-sorting";

const SKILL_SORTABLE_COLUMNS = [
  "name",
  "source",
  "category",
  "agent_count",
  "updated_at",
];

const extractErrorMessage = (error: unknown, fallback: string) => {
  if (error instanceof ApiError) return error.message || fallback;
  if (error instanceof Error) return error.message || fallback;
  return fallback;
};

export default function SkillsPage() {
  const { isSignedIn } = useAuth();
  const { isAdmin } = useOrganizationMembership(isSignedIn);
  const router = useRouter();
  const queryClient = useQueryClient();
  const { sorting, onSortingChange } = useUrlSorting({
    allowedColumnIds: SKILL_SORTABLE_COLUMNS,
    defaultSorting: [{ id: "name", desc: false }],
    paramPrefix: "skills",
  });

  const [deleteTarget, setDeleteTarget] = useState<SkillRead | null>(null);

  const skillsQuery = useListSkillsApiV1SkillsGet<
    listSkillsApiV1SkillsGetResponse,
    ApiError
  >(undefined, {
    query: {
      enabled: Boolean(isSignedIn),
      refetchOnMount: "always",
      refetchInterval: 30_000,
    },
  });
  const skills = useMemo(
    () =>
      skillsQuery.data?.status === 200
        ? (skillsQuery.data.data.items ?? [])
        : [],
    [skillsQuery.data],
  );
  const skillsKey = getListSkillsApiV1SkillsGetQueryKey();

  const deleteMutation = useDeleteSkillApiV1SkillsSkillIdDelete({
    mutation: {
      onSuccess: async () => {
        setDeleteTarget(null);
        await queryClient.invalidateQueries({ queryKey: skillsKey });
      },
    },
  });

  const handleDelete = () => {
    if (!deleteTarget) return;
    deleteMutation.mutate({ skillId: deleteTarget.id });
  };

  return (
    <>
      <DashboardPageLayout
        signedOut={{
          message: "Sign in to manage skills.",
          forceRedirectUrl: "/skills",
          signUpForceRedirectUrl: "/skills",
        }}
        title="Skills"
        description={`${skills.length} skill${skills.length === 1 ? "" : "s"} in the directory.`}
        headerActions={
          isAdmin ? (
            <div className="flex gap-3">
              <Link
                href="/skills/browse"
                className={buttonVariants({
                  size: "md",
                  variant: "outline",
                })}
              >
                Browse ClawHub
              </Link>
              <Link
                href="/skills/add"
                className={buttonVariants({ size: "md", variant: "primary" })}
              >
                New skill
              </Link>
            </div>
          ) : null
        }
        isAdmin={isAdmin}
        adminOnlyMessage="Only organization owners and admins can manage the skill directory."
        stickyHeader
      >
        <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
          <SkillsTable
            skills={skills}
            isLoading={skillsQuery.isLoading}
            sorting={sorting}
            onSortingChange={onSortingChange}
            stickyHeader
            onEdit={
              isAdmin
                ? (skill) => {
                    router.push(`/skills/${skill.id}/edit`);
                  }
                : undefined
            }
            onDelete={isAdmin ? setDeleteTarget : undefined}
            emptyState={{
              title: "No skills yet",
              description:
                "Create custom skills or import them from ClawHub to build your skill directory.",
              actionHref: isAdmin ? "/skills/add" : undefined,
              actionLabel: isAdmin ? "Create your first skill" : undefined,
            }}
          />
        </div>
        {skillsQuery.error ? (
          <p className="mt-4 text-sm text-rose-600">
            {skillsQuery.error.message}
          </p>
        ) : null}
      </DashboardPageLayout>

      <ConfirmActionDialog
        open={Boolean(deleteTarget)}
        onOpenChange={(open) => {
          if (!open) setDeleteTarget(null);
        }}
        ariaLabel="Delete skill"
        title="Delete skill"
        description={
          <>
            This will remove <strong>{deleteTarget?.name}</strong> from all
            assigned agents. This action cannot be undone.
          </>
        }
        errorMessage={
          deleteMutation.error
            ? extractErrorMessage(
                deleteMutation.error,
                "Unable to delete skill.",
              )
            : undefined
        }
        onConfirm={handleDelete}
        isConfirming={deleteMutation.isPending}
      />
    </>
  );
}
