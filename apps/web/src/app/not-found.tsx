import { ButtonLink, EmptyState } from "@/components/ui";

export default function NotFound() {
  return (
    <EmptyState
      title="Page not found"
      message="The page you're looking for doesn't exist."
      action={<ButtonLink href="/">Go home</ButtonLink>}
    />
  );
}
