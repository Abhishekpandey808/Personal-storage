import React, { useState, useEffect, useCallback } from "react";
import { API, Auth } from "aws-amplify";
import "./FileManager.css";

const API_NAME = "PersonalStorageApi";

export default function FileManager({ user }) {
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(null);

  const fetchFiles = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await API.get(API_NAME, "/files", {
        headers: { Authorization: `Bearer ${(await Auth.currentSession()).getIdToken().getJwtToken()}` },
      });
      setFiles(data.files || []);
    } catch (err) {
      setError("Failed to load files. Please try again.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchFiles();
  }, [fetchFiles]);

  const handleUpload = async (event) => {
    const file = event.target.files[0];
    if (!file) return;

    setUploading(true);
    setError(null);
    setSuccess(null);

    try {
      // Step 1: Request a pre-signed upload URL from the backend
      const token = (await Auth.currentSession()).getIdToken().getJwtToken();
      const data = await API.post(API_NAME, "/upload", {
        headers: { Authorization: `Bearer ${token}` },
        body: { filename: file.name, content_type: file.type || "application/octet-stream" },
      });

      // Step 2: Upload the file directly to S3 via the pre-signed URL
      await fetch(data.upload_url, {
        method: "PUT",
        headers: { "Content-Type": file.type || "application/octet-stream" },
        body: file,
      });

      setSuccess(`"${file.name}" uploaded successfully!`);
      fetchFiles();
    } catch (err) {
      setError("Upload failed. Please try again.");
    } finally {
      setUploading(false);
      event.target.value = "";
    }
  };

  const handleDownload = async (objectKey, fileName) => {
    setError(null);
    try {
      const token = (await Auth.currentSession()).getIdToken().getJwtToken();
      const data = await API.get(API_NAME, `/download?object_key=${encodeURIComponent(objectKey)}`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      // Open the pre-signed URL in a new tab to start the download
      window.open(data.download_url, "_blank", "noopener,noreferrer");
    } catch (err) {
      setError(`Failed to download "${fileName}".`);
    }
  };

  const handleDelete = async (objectKey, fileName) => {
    if (!window.confirm(`Delete "${fileName}"? This cannot be undone.`)) return;
    setError(null);
    try {
      const token = (await Auth.currentSession()).getIdToken().getJwtToken();
      await API.del(API_NAME, "/delete", {
        headers: { Authorization: `Bearer ${token}` },
        body: { object_key: objectKey },
      });
      setSuccess(`"${fileName}" deleted.`);
      setFiles((prev) => prev.filter((f) => f.object_key !== objectKey));
    } catch (err) {
      setError(`Failed to delete "${fileName}".`);
    }
  };

  const formatBytes = (bytes) => {
    if (bytes === 0) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return `${(bytes / k ** i).toFixed(1)} ${sizes[i]}`;
  };

  return (
    <div className="file-manager">
      <div className="fm-toolbar">
        <h2>My Files</h2>
        <label className={`upload-btn ${uploading ? "uploading" : ""}`}>
          {uploading ? "Uploading…" : "⬆ Upload File"}
          <input type="file" onChange={handleUpload} disabled={uploading} hidden />
        </label>
        <button className="refresh-btn" onClick={fetchFiles} disabled={loading}>
          ↻ Refresh
        </button>
      </div>

      {error && <div className="alert alert-error">{error}</div>}
      {success && <div className="alert alert-success">{success}</div>}

      {loading ? (
        <div className="loading">Loading files…</div>
      ) : files.length === 0 ? (
        <div className="empty-state">
          <p>No files yet. Upload your first file to get started!</p>
        </div>
      ) : (
        <table className="file-table">
          <thead>
            <tr>
              <th>Name</th>
              <th>Size</th>
              <th>Last Modified</th>
              <th>Actions</th>
            </tr>
          </thead>
          <tbody>
            {files.map((file) => (
              <tr key={file.object_key}>
                <td className="file-name">{file.name}</td>
                <td>{formatBytes(file.size)}</td>
                <td>{new Date(file.last_modified).toLocaleString()}</td>
                <td className="file-actions">
                  <button
                    className="btn-download"
                    onClick={() => handleDownload(file.object_key, file.name)}
                  >
                    ⬇ Download
                  </button>
                  <button
                    className="btn-delete"
                    onClick={() => handleDelete(file.object_key, file.name)}
                  >
                    🗑 Delete
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
