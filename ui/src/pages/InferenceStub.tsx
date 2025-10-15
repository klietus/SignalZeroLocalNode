import './InferenceStub.css';

const InferenceStub = () => {
  return (
    <main className="inference-stub">
      <section>
        <h1>Inference Console</h1>
        <p>
          This area will host inference queries against the Signal Zero reasoning stack. For now it
          is a placeholder so we can focus on the symbol browsing experience.
        </p>
        <div className="inference-stub__roadmap">
          <h2>Planned Features</h2>
          <ul>
            <li>Trigger on-demand inferences with configurable contexts.</li>
            <li>View streaming reasoning traces and token usage.</li>
            <li>Save common inference templates to reuse later.</li>
          </ul>
        </div>
      </section>
    </main>
  );
};

export default InferenceStub;
