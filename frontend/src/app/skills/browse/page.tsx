"use client";

export const dynamic = "force-dynamic";

import { useRouter } from "next/navigation";

import { useAuth } from "@/auth/clerk";
import { useQueryClient } from "@tanstack/react-query";

import { getListSkillsApiV1SkillsGetQueryKey } from "@/api/generated/skills/skills";
import { ClawHubBrowser } from "@/components/skills/ClawHubBrowser";
import { DashboardPageLayout } from "@/components/templates/DashboardPageLayout";
import { useOrganizationMembership } from "@/lib/use-organization-membership";

export default function BrowseClawHubPage() {
  const { isSignedIn } = useAuth();
  const { isAdmin } = useOrganizationMembership(isSignedIn);
  const router = useRouter();
  const queryClient = useQueryClient();
  const skillsKey = getListSkillsApiV1SkillsGetQueryKey();

  return (
    <DashboardPageLayout
      signedOut={{
        message: "Sign in to browse ClawHub skills.",
        forceRedirectUrl: "/skills/browse",
        signUpForceRedirectUrl: "/skills/browse",
      }}
      title="Browse ClawHub"
      description="Search the ClawHub registry and add skills to your directory."
      isAdmin={isAdmin}
      adminOnlyMessage="Only organization owners and admins can import skills."
    >
      <ClawHubBrowser
        onImported={async () => {
          await queryClient.invalidateQueries({ queryKey: skillsKey });
        }}
      />
    </DashboardPageLayout>
  );
}
