import { useEffect, useState } from 'react';
import { API_BASE_URL, api } from '../services/api';
import { Alert } from '../components/Alert.jsx';
import { formatDate } from '../utils/format.js';

export function HealthPage() {
  const [health, setHealth] = useState(null);
  const [error, setError] = useState('');

  async function load() {
    setError('');

    try {
      setHealth(await api.health());
    } catch (err) {
      setError(err.message);
    }
  }

  useEffect(() => {
    load();
  }, []);

  return (
    <section className="page">
      <div className="page-header">
        <div>
          <h1>Health & Monitoring</h1>
          <p>Backend health status and API connection metadata.</p>
        </div>
        <button className="secondary" type="button" onClick={load}>
          Refresh
        </button>
      </div>

      <Alert type="danger">{error}</Alert>

      <div className="panel health-panel">
        <h2>API Base URL</h2>
        <code>{API_BASE_URL}</code>
        <div className="health-grid">
          <Metric label="Status" value={health?.status || '--'} />
          <Metric label="Application" value={health?.app_name || '--'} />
          <Metric label="Version" value={health?.version || '--'} />
          <Metric label="Database" value={health?.database || '--'} />
          <Metric label="Redis" value={health?.redis || '--'} />
          <Metric label="Timestamp" value={health?.timestamp ? formatDate(health.timestamp) : '--'} />
        </div>
      </div>

      <div className="panel">
        <h2>Monitoring endpoints</h2>
        <p>Prometheus is exposed at <code>/metrics</code>. The built-in dashboard is available at <code>/api/v1/monitoring/dashboard</code>.</p>
      </div>
    </section>
  );
}

function Metric({ label, value }) {
  return (
    <div className="metric">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );
}
