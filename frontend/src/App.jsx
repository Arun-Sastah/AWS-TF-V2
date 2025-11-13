import React, { useState } from "react";

// Backend URL (from Vite env or default localhost)
const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

function App() {
  const [status, setStatus] = useState("");
  const [user, setUser] = useState("");
  const [device, setDevice] = useState("");
  const [loading, setLoading] = useState(false);
  const [instanceInfo, setInstanceInfo] = useState(null);

  // Call backend API
  const callAPI = async (endpoint) => {
    if (!user || !device) {
      setStatus("⚠️ Please enter both User and Device ID!");
      return;
    }

    setLoading(true);
    setStatus(`${endpoint === "deploy" ? "Creating" : "Destroying"} server...`);
    setInstanceInfo(null);

    try {
      const res = await fetch(`${API_URL}/${endpoint}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ user, device_id: device, instance_name: `${user}-${device}` }),
      });

      const data = await res.json();

      if (res.ok) {
        setStatus(`✅ ${data.message}`);

        // Check if backend returned outputs (Terraform outputs)
        if (data.outputs) {
          setInstanceInfo({
            id: data.outputs.ec2_instance_id?.value,
            ip: data.outputs.ec2_public_ip?.value,
            vpcId: data.outputs.vpc_id?.value,
            subnetId: data.outputs.subnet_id?.value,
            tableName: data.outputs.audit_table_name?.value,
          });
        }
      } else {
        // Show backend errors cleanly
        const errorMsg =
          typeof data.detail === "object"
            ? JSON.stringify(data.detail, null, 2)
            : data.detail;
        setStatus(`❌ ${errorMsg}`);
      }
    } catch (err) {
      setStatus(`⚠️ ${err.message}`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ textAlign: "center", marginTop: "50px", fontFamily: "Arial, sans-serif" }}>
      <h1>🚀 CosmicGen AWS Server Manager</h1>

      <div style={{ marginBottom: "20px" }}>
        <input
          placeholder="Enter User"
          value={user}
          onChange={(e) => setUser(e.target.value)}
          style={{ marginRight: "10px", padding: "5px" }}
        />
        <input
          placeholder="Enter Device ID"
          value={device}
          onChange={(e) => setDevice(e.target.value)}
          style={{ marginRight: "10px", padding: "5px" }}
        />
      </div>

      <div>
        <button
          onClick={() => callAPI("create-server")}
          disabled={loading}
          style={{ marginRight: "10px", padding: "10px 20px" }}
        >
          Create Server
        </button>
        <button
          onClick={() => callAPI("destroy-server")}
          disabled={loading}
          style={{
            padding: "10px 20px",
            backgroundColor: "#ff4d4f",
            color: "white",
            border: "none",
          }}
        >
          Destroy Server
        </button>
      </div>

      <div style={{ marginTop: "20px", fontWeight: "bold" }}>
        {loading ? "⏳ Working..." : status}
      </div>

      {instanceInfo && (
        <div style={{ marginTop: "20px", color: "green", textAlign: "left", display: "inline-block" }}>
          <h3>Instance Details:</h3>
          <p><strong>Instance ID:</strong> {instanceInfo.id}</p>
          <p><strong>Public IP:</strong> {instanceInfo.ip}</p>
          <p><strong>VPC ID:</strong> {instanceInfo.vpcId}</p>
          <p><strong>Subnet ID:</strong> {instanceInfo.subnetId}</p>
          <p><strong>Audit Table:</strong> {instanceInfo.tableName}</p>
        </div>
      )}
    </div>
  );
}

export default App;
