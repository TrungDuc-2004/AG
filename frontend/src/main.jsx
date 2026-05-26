import React, { useMemo, useState } from 'react';
import { createRoot } from 'react-dom/client';
import './styles.css';

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api';

const COLLECTIONS = {
  classes: {
    label: 'Class',
    endpoint: '/classes',
    description: 'Tạo metadata lớp học. Class không bắt buộc có file trong thiết kế hiện tại.',
    submitText: 'Tạo Class',
    initial: {
      map_id: '11',
      name: 'Lớp 11',
    },
    fields: [
      { name: 'map_id', label: 'map_id', required: true, placeholder: 'VD: 11' },
      { name: 'name', label: 'name', required: true, placeholder: 'VD: Lớp 11' },
    ],
  },
  users: {
    label: 'User',
    endpoint: '/users',
    description: 'Tạo người dùng. Role chỉ là field trong users, không tạo collection roles.',
    submitText: 'Tạo User',
    initial: {
      map_id: 'USER_001',
      name: 'Nguyễn Văn A',
      email: 'nguyenvana@example.com',
      role: 'user',
      gender: '',
      address: '',
      birthDate: '',
      avatarImage: '',
    },
    fields: [
      { name: 'map_id', label: 'map_id', required: true, placeholder: 'VD: USER_001' },
      { name: 'name', label: 'name', required: true, placeholder: 'VD: Nguyễn Văn A' },
      { name: 'email', label: 'email', required: true, type: 'email', placeholder: 'VD: user@example.com' },
      { name: 'role', label: 'role', required: true, placeholder: 'VD: user / admin / giáo viên' },
      { name: 'gender', label: 'gender', placeholder: 'VD: male / female' },
      { name: 'birthDate', label: 'birthDate', type: 'date' },
      { name: 'address', label: 'address' },
      { name: 'avatarImage', label: 'avatarImage', placeholder: 'URL ảnh đại diện nếu có' },
    ],
  },
  subjects: {
    label: 'Subject',
    endpoint: '/subjects',
    description: 'Tạo môn học. FilePath sẽ do backend tự sinh nếu bạn upload file.',
    submitText: 'Tạo Subject',
    fileLabel: 'Upload file cấp Subject nếu có',
    fileRequired: false,
    initial: {
      map_id: 'HH11',
      name: 'Hóa học',
      classMapId: '11',
      description: 'Học liệu STEM môn Hóa học lớp 11',
    },
    fields: [
      { name: 'map_id', label: 'map_id', required: true, placeholder: 'VD: HH11' },
      { name: 'name', label: 'name', required: true, placeholder: 'VD: Hóa học' },
      { name: 'classMapId', label: 'classMapId', required: true, placeholder: 'VD: 11' },
      { name: 'description', label: 'description', kind: 'textarea' },
    ],
  },
  topics: {
    label: 'Topic',
    endpoint: '/topics',
    description: 'Tạo chủ đề STEM thuộc một môn học. FilePath sẽ do backend tự sinh nếu bạn upload file tổng quan chủ đề.',
    submitText: 'Tạo Topic',
    fileLabel: 'Upload file cấp Topic nếu có',
    fileRequired: false,
    initial: {
      map_id: 'HH11_T1',
      subjectMapId: 'HH11',
      name: 'Nước và dung dịch',
      description: 'Chủ đề STEM về nước, dung dịch và xử lý nước',
      topicNumber: '1',
      periodCount: '3',
    },
    fields: [
      { name: 'map_id', label: 'map_id', required: true, placeholder: 'VD: HH11_T1' },
      { name: 'subjectMapId', label: 'subjectMapId', required: true, placeholder: 'VD: HH11' },
      { name: 'name', label: 'name', required: true, placeholder: 'VD: Nước và dung dịch' },
      { name: 'topicNumber', label: 'topicNumber', type: 'number' },
      { name: 'periodCount', label: 'periodCount', type: 'number' },
      { name: 'description', label: 'description', kind: 'textarea' },
    ],
  },
  concepts: {
    label: 'Concept',
    endpoint: '/concepts',
    description: 'Tạo kiến thức nền/khái niệm thuộc một topic. FilePath sẽ do backend tự sinh nếu bạn upload file lý thuyết.',
    submitText: 'Tạo Concept',
    fileLabel: 'Upload file cấp Concept nếu có',
    fileRequired: false,
    initial: {
      map_id: 'HH11_T1_C1',
      topicMapId: 'HH11_T1',
      name: 'Lọc nước và hấp phụ',
      definition: 'Kiến thức nền về lọc nước, vật liệu hấp phụ và xử lý nước.',
      conceptNumber: '1',
    },
    fields: [
      { name: 'map_id', label: 'map_id', required: true, placeholder: 'VD: HH11_T1_C1' },
      { name: 'topicMapId', label: 'topicMapId', required: true, placeholder: 'VD: HH11_T1' },
      { name: 'name', label: 'name', required: true, placeholder: 'VD: Lọc nước và hấp phụ' },
      { name: 'conceptNumber', label: 'conceptNumber', type: 'number' },
      { name: 'definition', label: 'definition', kind: 'textarea' },
    ],
  },
  documents: {
    label: 'Document',
    endpoint: '/documents',
    description: 'Tạo học liệu cụ thể và upload file gốc lên Google Drive. createdBy, updatedBy, sourceName, sourceUrl, language và licenseNote được backend tự xử lý/default.',
    submitText: 'Tạo Document + Upload file',
    fileLabel: 'Upload file gốc của Document',
    fileRequired: true,
    initial: {
      map_id: 'HH11_T1_C1_D1',
      title: 'Bình lọc nước',
      conceptMapId: 'HH11_T1_C1',
      typedocs: '1',
      description: 'Học liệu STEM thiết kế bình lọc nước.',
      keysearch: 'stem hóa học lớp 11 bình lọc nước hấp phụ',
    },
    fields: [
      { name: 'map_id', label: 'map_id', required: true, placeholder: 'VD: HH11_T1_C1_D1' },
      { name: 'title', label: 'title', required: true, placeholder: 'VD: Bình lọc nước' },
      { name: 'conceptMapId', label: 'conceptMapId', required: true, placeholder: 'VD: HH11_T1_C1' },
      { name: 'typedocs', label: 'typedocs', required: true, placeholder: 'VD: 1 = document, 2 = image, 3 = video' },
      { name: 'description', label: 'description', kind: 'textarea' },
      { name: 'keysearch', label: 'keysearch', kind: 'textarea' },
    ],
  },
};

function buildInitialForms() {
  return Object.fromEntries(
    Object.entries(COLLECTIONS).map(([key, config]) => [key, { ...config.initial }])
  );
}

function appendFormFields(data, form) {
  Object.entries(form).forEach(([key, value]) => {
    if (value !== undefined && value !== null && value !== '') {
      data.append(key, value);
    }
  });
}

function FieldRenderer({ field, value, onChange }) {
  const commonProps = {
    name: field.name,
    value: value ?? '',
    onChange: e => onChange(field.name, e.target.value),
    placeholder: field.placeholder || '',
    required: Boolean(field.required),
  };

  return (
    <label className={`field ${field.kind === 'textarea' ? 'field-wide' : ''}`}>
      <span>
        {field.label}
        {field.required && <em>*</em>}
      </span>
      {field.kind === 'textarea' ? (
        <textarea {...commonProps} rows={3} />
      ) : (
        <input {...commonProps} type={field.type || 'text'} />
      )}
    </label>
  );
}

function App() {
  const [selectedCollection, setSelectedCollection] = useState('documents');
  const [forms, setForms] = useState(() => buildInitialForms());
  const [files, setFiles] = useState({});
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);

  const currentConfig = COLLECTIONS[selectedCollection];
  const currentForm = forms[selectedCollection];

  const selectedSummary = useMemo(() => {
    if (selectedCollection === 'classes') return 'Class: tạo lớp học.';
    if (selectedCollection === 'users') return 'User: tạo người dùng.';
    if (selectedCollection === 'subjects') return 'Subject: tạo môn học, file tùy chọn.';
    if (selectedCollection === 'topics') return 'Topic: tạo chủ đề STEM, file tùy chọn.';
    if (selectedCollection === 'concepts') return 'Concept: tạo kiến thức nền, file tùy chọn.';
    return 'Document: tạo học liệu và bắt buộc upload file gốc.';
  }, [selectedCollection]);

  function updateField(name, value) {
    setForms(prev => ({
      ...prev,
      [selectedCollection]: {
        ...prev[selectedCollection],
        [name]: value,
      },
    }));
  }

  function updateFile(file) {
    setFiles(prev => ({
      ...prev,
      [selectedCollection]: file,
    }));
  }

  async function seedData() {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/seed/mongo-sample`, { method: 'POST' });
      const payload = await res.json();
      setResult({ ok: res.ok, status: res.status, endpoint: '/seed/mongo-sample', payload });
    } catch (err) {
      setResult({ ok: false, error: String(err) });
    } finally {
      setLoading(false);
    }
  }

  async function submitSelectedCollection(event) {
    event.preventDefault();

    const selectedFile = files[selectedCollection];
    if (currentConfig.fileRequired && !selectedFile) {
      alert('Bạn cần chọn file gốc cho Document');
      return;
    }

    setLoading(true);
    try {
      const data = new FormData();
      appendFormFields(data, currentForm);
      if (selectedFile) data.append('file', selectedFile);

      const res = await fetch(`${API_BASE}${currentConfig.endpoint}`, {
        method: 'POST',
        body: data,
      });
      const payload = await res.json();
      setResult({
        ok: res.ok,
        status: res.status,
        collection: selectedCollection,
        endpoint: currentConfig.endpoint,
        payload,
      });
    } catch (err) {
      setResult({ ok: false, error: String(err) });
    } finally {
      setLoading(false);
    }
  }


  async function callSync(endpoint, method = 'GET') {
    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}${endpoint}`, { method });
      const payload = await res.json();
      setResult({ ok: res.ok, status: res.status, endpoint, payload });
    } catch (err) {
      setResult({ ok: false, error: String(err) });
    } finally {
      setLoading(false);
    }
  }

  function resetCurrentForm() {
    setForms(prev => ({
      ...prev,
      [selectedCollection]: { ...currentConfig.initial },
    }));
    setFiles(prev => ({ ...prev, [selectedCollection]: null }));
  }

  return (
    <div className="container">
      <header className="hero">
        <div>
          <h1>STEM Learning Resources</h1>
          <p>
            Chọn collection cần nhập, form sẽ tự đổi các trường tương ứng. File upload sẽ được lưu lên Google Drive theo cấu trúc logic
            <b> STEM / class / subjects|topics|concepts|documents / entity / file</b>.
          </p>
        </div>
        <div className="hero-actions">
          <button type="button" onClick={seedData} disabled={loading}>Seed dữ liệu mẫu</button>
          <button type="button" className="secondary" onClick={() => callSync('/sync/check-mongo')} disabled={loading}>Check Mongo</button>
          <button type="button" className="secondary" onClick={() => callSync('/sync/init-targets', 'POST')} disabled={loading}>Init PG/Neo4j</button>
          <button type="button" className="secondary" onClick={() => callSync('/sync/all', 'POST')} disabled={loading}>Sync all</button>
        </div>
      </header>

      <section className="card selector-card">
        <label className="collection-select">
          <span>Chọn collection cần nhập</span>
          <select
            value={selectedCollection}
            onChange={e => setSelectedCollection(e.target.value)}
            disabled={loading}
          >
            {Object.entries(COLLECTIONS).map(([key, config]) => (
              <option key={key} value={key}>{config.label}</option>
            ))}
          </select>
        </label>
        <p className="selected-summary">{selectedSummary}</p>
      </section>

      <section className="card form-card">
        <div className="form-heading">
          <div>
            <h2>Nhập collection: {currentConfig.label}</h2>
            <p className="note">{currentConfig.description}</p>
          </div>
          <button type="button" className="secondary" onClick={resetCurrentForm} disabled={loading}>
            Reset form này
          </button>
        </div>

        <form onSubmit={submitSelectedCollection}>
          <div className="grid">
            {currentConfig.fields.map(field => (
              <FieldRenderer
                key={field.name}
                field={field}
                value={currentForm[field.name]}
                onChange={updateField}
              />
            ))}

            {currentConfig.fileLabel && (
              <label className="field field-wide">
                <span>
                  {currentConfig.fileLabel}
                  {currentConfig.fileRequired && <em>*</em>}
                </span>
                <input
                  type="file"
                  onChange={e => updateFile(e.target.files?.[0] || null)}
                  required={Boolean(currentConfig.fileRequired)}
                />
                {files[selectedCollection]?.name && (
                  <small>Đã chọn: {files[selectedCollection].name}</small>
                )}
              </label>
            )}
          </div>

          <button type="submit" disabled={loading}>
            {loading ? 'Đang xử lý...' : currentConfig.submitText}
          </button>
        </form>
      </section>

      <section className="card">
        <h2>Kết quả API</h2>
        <pre>{result ? JSON.stringify(result, null, 2) : 'Chưa có dữ liệu'}</pre>
      </section>
    </div>
  );
}

createRoot(document.getElementById('root')).render(<App />);
