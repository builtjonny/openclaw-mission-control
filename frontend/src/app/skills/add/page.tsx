"use client";

export const dynamic = "force-dynamic";

import { useRouter } from "next/navigation";

import { useAuth } from "@/auth/clerk";

import { ApiError } from "@/api/mutator";
import { useCreateSkillApiV1SkillsPost } from "@/api/generated/skills/skills";
import { SkillForm } from "@/components/skills/SkillForm";
import { DashboardPageLayout } from "@/components/templates/DashboardPageLayout";
import { useOrganizationMembership } from "@/lib/use-organization-membership";

export default function NewSkillPage() {
  const router = useRouter();
  const { isSignedIn } = useAuth();
  const { isAdmin } = useOrganizationMembership(isSignedIn);

  const createMutation = useCreateSkillApiV1SkillsPost<ApiError>({
    mutation: {
      retry: false,
    },
  });

  return (
    <DashboardPageLayout
      signedOut={{
        message: "Sign in to create skills.",
        forceRedirectUrl: "/skills/add",
        signUpForceRedirectUrl: "/skills/add",
      }}
      title="Create skill"
      description="Define a custom skill with instructions for agents."
      isAdmin={isAdmin}
      adminOnlyMessage="Only organization owners and admins can manage the skill directory."
    >
      <SkillForm
        isSubmitting={createMutation.isPending}
        submitLabel="Create skill"
        submittingLabel="Creating..."
        onCancel={() => router.push("/skills")}
        onSubmit={async (values) => {
          const result = await createMutation.mutateAsync({
            data: values,
          });
          if (result.status !== 200) {
            throw new Error("Unable to create skill.");
          }
          router.push("/skills");
        }}
      />
    </DashboardPageLayout>
  );
}
