import AppShell from '@/components/AppShell';
import ErrorBoundary from '@/components/ErrorBoundary';

export default function Home() {
  return (
    <ErrorBoundary>
      <AppShell />
    </ErrorBoundary>
  );
}
