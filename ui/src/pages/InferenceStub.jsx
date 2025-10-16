const InferenceStub = () => {
  return (
    <section className="mx-auto flex w-full max-w-4xl flex-1 px-6 py-12">
      <div className="flex w-full flex-col gap-6 rounded-2xl border border-slate-800 bg-slate-900/60 p-8 shadow-lg shadow-slate-950/30 backdrop-blur">
        <div className="space-y-2">
          <h1 className="text-3xl font-semibold tracking-tight text-white">Inference Console</h1>
          <p className="text-sm leading-relaxed text-slate-300">
            This area will host inference queries against the Signal Zero reasoning stack. For now it
            is a placeholder so we can focus on the symbol browsing experience.
          </p>
        </div>
        <div className="space-y-4">
          <h2 className="text-lg font-semibold text-white">Planned Features</h2>
          <ul className="list-disc space-y-2 pl-5 text-sm text-slate-200">
            <li>Trigger on-demand inferences with configurable contexts.</li>
            <li>View streaming reasoning traces and token usage.</li>
            <li>Save common inference templates to reuse later.</li>
          </ul>
        </div>
      </div>
    </section>
  );
};

export default InferenceStub;
