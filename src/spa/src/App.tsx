import PdfTrainingWizard from "./pages/PdfTrainingWizard";

function App() {
  return (
    <div className="app-shell">
      <header className="app-header">
        <h1>PDF Training Assistant</h1>
        <p>
          Four-step assistant guiding you through upload, analyze, review, and
          retrain without leaving this screen.
        </p>
      </header>
      <main className="app-content">
        <PdfTrainingWizard />
      </main>
    </div>
  );
}

export default App;
