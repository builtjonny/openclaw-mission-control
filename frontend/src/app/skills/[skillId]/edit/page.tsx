"use client";

export const dynamic = "force-dynamic";

import { useMemo } from "react";
import { useParams, useRouter } from "next/navigation";

import { useAuth } from "@/auth/clerk";

import { ApiError } from "@/api/mutator";
import {
  type getSkillApiV1SkillsSkillIdGetResponse,
  useGetSkillApiV1SkillsSkillIdGet,
  useUpdateSkillApiV1SkillsSkillIdPatch,
} from "@/api/generated/skills/skills";
import { SkillForm } from "@/components/skills/SkillForm";
import { DashboardPageLayout } from "@/components/templates/DashboardPageLayout";
import { useOrganizationMembership } from "@/lib/use-organization-membership";

export default function EditSkillPage() {
  const router = useRouter();
  const params = useParams();
  const skillIdParam = params?.skillId;
  const skillId = Array.isArray(skillIdParam) ? skillIdParam[0] : skillIdParam;
  const { isSignedIn } = useAuth();
  const { isAdmin } = useOrganizationMembership(isSignedIn);

  const skillQuery = useGetSkillApiV1SkillsSkillIdGet<
    getSkillApiV1SkillsSkillIdGetResponse,
    ApiError
  >(skillId ?? "", {
    query: {
      enabled: Boolean(isSignedIn && skillId),
      refetchOnMount: "always",
      retry: false,
    },
  });

  const updateMutation = useUpdateSkillApiV1SkillsSkillIdPatch<ApiError>({
    mutation: {
      retry: false,
    },
  });

  const skill = useMemo(
    () => (skillQuery.data?.status === 200 ? skillQuery.data.data : null),
    [skillQuery.data],
  );

  return (
    <DashboardPageLayout
      signedOut={{
        message: "Sign in to edit skills.",
        forceRedirectUrl: `/skills/${skillId ?? ""}/edit`,
        signUpForceRedirectUrl: `/skills/${skillId ?? ""}/edit`,
      }}
      title={skill ? `Edit ${skill.name}` : "Edit skill"}
      description="Update skill details and instructions."
      isAdmin={isAdmin}
      adminOnlyMessage="Only organization owners and admins can manage the skill directory."
    >
      {skillQuery.isLoading ? (
        <div className="rounded-xl border border-slate-200 bg-white p-6 text-sm text-slate-500 shadow-sm">
          Loading skill...
        </div>
      ) : skillQuery.error ? (
        <div className="rounded-xl border border-rose-200 bg-rose-50 p-6 text-sm text-rose-700 shadow-sm">
          {skillQuery.error.message}
        </div>
      ) : !skill ? (
        <div className="rounded-xl border border-slate-200 bg-white p-6 text-sm text-slate-500 shadow-sm">
          Skill not found.
        </div>
      ) : (
        <SkillForm
          initialValues={{
            name: skill.name,
            slug: skill.slug,
            summary: skill.summary ?? "",
            instructions: skill.instructions ?? "",
            category: skill.category ?? "",
          }}
          isSubmitting={updateMutation.isPending}
          submitLabel="Save changes"
          submittingLabel="Saving..."
          onCancel={() => router.push("/skills")}
          onSubmit={async (values) => {
            const result = await updateMutation.mutateAsync({
              skillId: skill.id,
              data: values,
            });
            if (result.status !== 200) {
              throw new Error("Unable to update skill.");
            }
            router.push("/skills");
          }}
        />
      )}
    </DashboardPageLayout>
  );
}
