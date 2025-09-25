import PdfTrainingWizard from "./pages/PdfTrainingWizard";
import { Toaster } from "./components/ui/toaster";

function App() {
  return (
    <div className="min-h-screen bg-background text-foreground">
      <div className="container flex min-h-screen max-w-6xl flex-col gap-8 py-10">
        <header className="flex flex-col gap-4 text-center sm:text-left">
          <div>
            <p className="text-sm font-semibold text-muted-foreground uppercase tracking-wide">
              Workflow
            </p>
            <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">
              PDF Training Assistant
            </h1>
          </div>
          <p className="text-base text-muted-foreground sm:max-w-2xl">
            Upload new documents, review annotations, and trigger retraining in a
            single workspace powered by Tailwind CSS and shadcn/ui.
          </p>
        </header>
        <main className="flex-1">
          <PdfTrainingWizard />
        </main>
      </div>
      <Toaster />
    </div>
  );
}

export default App;
