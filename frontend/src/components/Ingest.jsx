import React, { useState } from 'react';
import { ingestData } from '../api';
import { UploadCloud, CheckCircle, AlertCircle } from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const Ingest = () => {
  const [domain, setDomain] = useState('');
  const [file, setFile] = useState(null);
  const [status, setStatus] = useState(null); // { type: 'success' | 'error', msg: '' }
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setStatus(null);
    try {
      if (!file) {
        setStatus({ type: 'error', msg: 'Please select a file to upload.' });
        setLoading(false);
        return;
      }
      const data = await ingestData(domain, file);
      setStatus({ type: 'success', msg: data.message });
      setDomain('');
      setFile(null);
      // Reset the file input element if needed
      document.getElementById('file-upload').value = '';
    } catch (err) {
      setStatus({ type: 'error', msg: err.response?.data?.detail || 'Ingestion failed.' });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={{ padding: '30px', maxWidth: '800px', margin: '0 auto' }}>
      <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
        <h2 style={{ marginBottom: '20px', fontSize: '2rem', background: 'linear-gradient(135deg, #f8fafc, var(--cyan))', WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent', fontWeight: 700 }}>
          Ingest Knowledge
        </h2>
        <p style={{ color: 'var(--text-muted)', marginBottom: '30px' }}>
          Upload documents (.txt, .pdf, .docx) into specific namespaces. Access control applies based on your roles.
        </p>
      </motion.div>

      <AnimatePresence>
        {status && (
          <motion.div 
            initial={{ opacity: 0, scale: 0.9, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.9, y: -10 }}
            style={{
              padding: '16px',
              borderRadius: '8px',
              marginBottom: '20px',
              display: 'flex',
              alignItems: 'center',
              gap: '12px',
              background: status.type === 'success' ? 'rgba(16, 185, 129, 0.1)' : 'rgba(239, 68, 68, 0.1)',
              border: `1px solid ${status.type === 'success' ? 'var(--success)' : 'var(--danger)'}`,
              color: status.type === 'success' ? 'var(--success)' : 'var(--danger)'
            }}
          >
            {status.type === 'success' ? <CheckCircle size={20} /> : <AlertCircle size={20} />}
            {status.msg}
          </motion.div>
        )}
      </AnimatePresence>

      <motion.form 
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5, delay: 0.1 }}
        onSubmit={handleSubmit} 
        className="glass-panel" 
        style={{ padding: '30px' }}
      >
        <div className="input-group">
          <label>Target Namespace / Domain</label>
          <select
            className="input-field"
            value={domain}
            onChange={(e) => setDomain(e.target.value)}
            required
          >
            <option value="" disabled>Select Domain</option>
            <option value="IT">IT</option>
            <option value="HR">HR</option>
          </select>
        </div>

        <div className="input-group">
          <label>File Upload (.txt, .pdf, .docx)</label>
          <input
            id="file-upload"
            type="file"
            className="input-field"
            accept=".txt,.pdf,.docx"
            onChange={(e) => setFile(e.target.files[0])}
            required
            style={{ padding: '12px', cursor: 'pointer' }}
          />
          {file && (
            <div style={{ marginTop: '10px', fontSize: '0.9rem', color: 'var(--cyan)' }}>
              Selected file: {file.name} ({(file.size / 1024).toFixed(2)} KB)
            </div>
          )}
        </div>

        <motion.button 
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3 }}
          whileHover={{ scale: 1.02, boxShadow: '0 0 20px rgba(6, 182, 212, 0.5)' }}
          whileTap={{ scale: 0.98 }}
          type="submit" 
          className="btn btn-primary" 
          style={{ width: '100%', marginTop: '20px', padding: '14px', fontSize: '1rem' }} 
          disabled={loading}
        >
          {loading ? 'Processing...' : <><UploadCloud size={18} /> Ingest Data</>}
        </motion.button>
      </motion.form>
    </div>
  );
};

export default Ingest;
