import { Check, ChevronDown, RefreshCw, X } from 'lucide-react';
import { useEffect, useState } from 'react';
import {
  DEFAULT_API_BASE,
  getFeedback,
  updateFeedbackStatus,
} from '../lib/api';
import { clsx } from '../lib/utils';

type FeedbackItem = {
  id: string;
  timestamp: string;
  type: string;
  message: string;
  city: string | null;
  region: string | null;
  category: string | null;
  original_query: string | null;
  original_answer: string | null;
  status: string;
  validation: unknown;
};

const FILTERS = [
  { value: 'all', label: 'All' },
  { value: 'pending', label: 'Pending' },
  { value: 'needs_review', label: 'Needs Review' },
  { value: 'approved', label: 'Approved' },
  { value: 'rejected', label: 'Rejected' },
];

function formatDate(value: string) {
  const date = new Date(value);

  if (Number.isNaN(date.getTime())) {
    return value;
  }

  return date.toLocaleString();
}

function formatType(type: string) {
  return type
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function getStatusClass(status: string) {
  if (status === 'approved') return 'status-approved';
  if (status === 'rejected') return 'status-rejected';
  if (status === 'needs_review') return 'status-review';
  return 'status-pending';
}

export default function Feedback() {
  const [items, setItems] = useState<FeedbackItem[]>([]);
  const [filter, setFilter] = useState('all');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [updating, setUpdating] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<string | null>(null);

  async function loadFeedback() {
    setLoading(true);
    setError('');

    try {
      const data = await getFeedback(DEFAULT_API_BASE, filter);
      setItems(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error(err);
      setError('Could not load feedback.');
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void loadFeedback();
  }, [filter]);

  async function handleStatus(
    id: string,
    action: 'approve' | 'reject',
  ) {
    setUpdating(id);

    try {
      await updateFeedbackStatus(
        DEFAULT_API_BASE,
        id,
        action,
      );

      setExpanded(null);
      await loadFeedback();
    } catch (err) {
      console.error(err);
      setError('Could not update feedback.');
    } finally {
      setUpdating(null);
    }
  }

  function toggleExpanded(id: string) {
    setExpanded((current) => (current === id ? null : id));
  }

  return (
    <div className="page feedback-page">
      <style>{`
        .feedback-page {
          max-width: 1100px;
          margin: 0 auto;
          padding-bottom: 48px;
        }

        .feedback-page .page-head {
          margin-bottom: 24px;
        }

        .feedback-page .page-head h1 {
          margin-bottom: 6px;
        }

        .feedback-filters {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
          margin-bottom: 24px;
        }

        .feedback-filters .chip-btn {
          border: 1px solid rgba(14, 59, 46, 0.16);
          background: rgba(255, 255, 255, 0.55);
          color: #365046;
          border-radius: 999px;
          padding: 8px 16px;
          font-size: 13px;
          font-weight: 600;
          cursor: pointer;
          transition: 0.18s ease;
        }

        .feedback-filters .chip-btn:hover {
          transform: translateY(-1px);
          background: rgba(255, 255, 255, 0.85);
        }

        .feedback-filters .chip-btn.is-on {
          background: #0e3b2e;
          color: #fff;
          border-color: #0e3b2e;
        }

        .feedback-list {
          display: flex;
          flex-direction: column;
          gap: 14px;
        }

        .feedback-card {
          overflow: hidden;
          border: 1px solid rgba(72, 63, 47, 0.14);
          border-radius: 18px;
          background: rgba(255, 252, 246, 0.92);
          box-shadow: 0 5px 20px rgba(61, 51, 35, 0.07);
          transition:
            transform 0.18s ease,
            box-shadow 0.18s ease,
            border-color 0.18s ease;
        }

        .feedback-card:hover {
          transform: translateY(-1px);
          box-shadow: 0 8px 24px rgba(61, 51, 35, 0.1);
          border-color: rgba(14, 59, 46, 0.22);
        }

        .feedback-card-main {
          width: 100%;
          border: 0;
          background: transparent;
          text-align: left;
          padding: 20px 22px 16px;
          cursor: pointer;
          color: inherit;
        }

        .feedback-card-head {
          display: flex;
          align-items: flex-start;
          justify-content: space-between;
          gap: 16px;
          margin-bottom: 14px;
        }

        .feedback-card-title {
          display: flex;
          align-items: center;
          gap: 9px;
          flex-wrap: wrap;
        }

        .feedback-type {
          color: #0e3b2e;
          font-size: 13px;
          font-weight: 800;
          letter-spacing: 0.01em;
        }

        .feedback-status {
          display: inline-flex;
          align-items: center;
          border-radius: 999px;
          padding: 4px 9px;
          font-size: 11px;
          font-weight: 700;
        }

        .status-pending {
          background: #f1e5bd;
          color: #765b13;
        }

        .status-review {
          background: #dce8e4;
          color: #0e3b2e;
        }

        .status-approved {
          background: #dcebdd;
          color: #28613b;
        }

        .status-rejected {
          background: #f1dada;
          color: #9a3434;
        }

        .feedback-date {
          color: #817969;
          font-size: 12px;
          white-space: nowrap;
        }

        .feedback-preview {
          color: #403a31;
          font-size: 14px;
          line-height: 1.7;
          margin-bottom: 8px;
        }

        .feedback-question-preview {
          color: #71695d;
          font-size: 13px;
          line-height: 1.6;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }

        .feedback-expand {
          display: flex;
          align-items: center;
          gap: 6px;
          margin-top: 12px;
          color: #0e3b2e;
          font-size: 12px;
          font-weight: 700;
        }

        .feedback-expand svg {
          transition: transform 0.2s ease;
        }

        .feedback-expand.is-open svg {
          transform: rotate(180deg);
        }

        .feedback-details {
          border-top: 1px solid rgba(72, 63, 47, 0.1);
          padding: 18px 22px 20px;
          background: rgba(246, 241, 232, 0.72);
        }

        .feedback-section {
          margin-bottom: 16px;
        }

        .feedback-section:last-child {
          margin-bottom: 0;
        }

        .feedback-label {
          margin-bottom: 6px;
          color: #847b6d;
          font-size: 11px;
          font-weight: 800;
          letter-spacing: 0.06em;
          text-transform: uppercase;
        }

        .feedback-content {
          color: #39342c;
          font-size: 13px;
          line-height: 1.7;
          white-space: pre-wrap;
        }

        .feedback-meta {
          display: flex;
          flex-wrap: wrap;
          gap: 8px;
          margin-top: 16px;
        }

        .feedback-meta span {
          padding: 6px 10px;
          border-radius: 8px;
          background: rgba(14, 59, 46, 0.07);
          color: #40544c;
          font-size: 11px;
          font-weight: 600;
        }

        .feedback-actions {
          display: flex;
          justify-content: flex-end;
          gap: 10px;
          padding: 14px 22px 18px;
          border-top: 1px solid rgba(72, 63, 47, 0.1);
          background: rgba(255, 252, 246, 0.7);
        }

        .feedback-actions .btn {
          min-width: 105px;
          justify-content: center;
          border-radius: 10px;
          font-weight: 700;
        }

        .feedback-actions .approve-btn {
          background: #2f6b43;
          border-color: #2f6b43;
          color: white;
        }

        .feedback-actions .approve-btn:hover {
          background: #255936;
        }

        .feedback-actions .reject-btn {
          background: #a43d3d;
          border-color: #a43d3d;
          color: white;
        }

        .feedback-actions .reject-btn:hover {
          background: #8d3333;
        }

        .feedback-error {
          margin-bottom: 18px;
          padding: 12px 14px;
          border-radius: 10px;
          background: #f5dddd;
          color: #8d3333;
          font-size: 13px;
        }

        .feedback-empty {
          padding: 48px 20px;
          text-align: center;
          border: 1px dashed rgba(72, 63, 47, 0.2);
          border-radius: 16px;
          color: #817969;
          background: rgba(255, 252, 246, 0.55);
        }

        [data-theme="dark"] .feedback-card {
          background: rgba(13, 38, 28, 0.94);
          border-color: rgba(255, 255, 255, 0.08);
        }

        [data-theme="dark"] .feedback-card-main {
          color: #e6dfd3;
        }

        [data-theme="dark"] .feedback-preview,
        [data-theme="dark"] .feedback-content {
          color: #ddd5c8;
        }

        [data-theme="dark"] .feedback-question-preview {
          color: #aaa193;
        }

        [data-theme="dark"] .feedback-details {
          background: rgba(5, 20, 14, 0.65);
          border-color: rgba(255, 255, 255, 0.08);
        }

        [data-theme="dark"] .feedback-actions {
          background: rgba(13, 38, 28, 0.8);
          border-color: rgba(255, 255, 255, 0.08);
        }

        [data-theme="dark"] .feedback-filters .chip-btn {
          background: rgba(13, 38, 28, 0.8);
          color: #d8cfbf;
          border-color: rgba(255, 255, 255, 0.1);
        }

        [data-theme="dark"] .feedback-filters .chip-btn.is-on {
          background: #0e3b2e;
          color: #fff;
        }

        @media (max-width: 700px) {
          .feedback-card-head {
            flex-direction: column;
            gap: 8px;
          }

          .feedback-date {
            white-space: normal;
          }

          .feedback-actions {
            flex-direction: column;
          }

          .feedback-actions .btn {
            width: 100%;
          }
        }
      `}</style>

      <div className="page-head">
        <div>
          <p className="eyebrow">ASEEL</p>
          <h1>Feedback</h1>
          <p className="muted">
            Review user feedback and manage improvement requests.
          </p>
        </div>

        <button
          type="button"
          className="btn btn-quiet"
          onClick={() => void loadFeedback()}
          disabled={loading}
        >
          <RefreshCw size={16} />
          Refresh
        </button>
      </div>

      <div className="feedback-filters">
        {FILTERS.map((item) => (
          <button
            key={item.value}
            type="button"
            className={clsx(
              'chip-btn',
              filter === item.value && 'is-on',
            )}
            onClick={() => setFilter(item.value)}
          >
            {item.label}
          </button>
        ))}
      </div>

      {error && (
        <div className="feedback-error">
          {error}
        </div>
      )}

      {loading ? (
        <div className="feedback-empty">
          Loading feedback...
        </div>
      ) : items.length === 0 ? (
        <div className="feedback-empty">
          No feedback found.
        </div>
      ) : (
        <div className="feedback-list">
          {items.map((item) => {
            const isOpen = expanded === item.id;
            const canReview =
              item.status === 'pending' ||
              item.status === 'needs_review';

            return (
              <article
                key={item.id}
                className="feedback-card"
              >
                <button
                  type="button"
                  className="feedback-card-main"
                  onClick={() => toggleExpanded(item.id)}
                  aria-expanded={isOpen}
                >
                  <div className="feedback-card-head">
                    <div className="feedback-card-title">
                      <span className="feedback-type">
                        {formatType(item.type)}
                      </span>

                      <span
                        className={clsx(
                          'feedback-status',
                          getStatusClass(item.status),
                        )}
                      >
                        {formatType(item.status)}
                      </span>
                    </div>

                    <span className="feedback-date">
                      {formatDate(item.timestamp)}
                    </span>
                  </div>

                  <div className="feedback-preview">
                    {item.message || 'No message provided.'}
                  </div>

                  {item.original_query && (
                    <div className="feedback-question-preview">
                      {item.original_query}
                    </div>
                  )}

                  <div
                    className={clsx(
                      'feedback-expand',
                      isOpen && 'is-open',
                    )}
                  >
                    <span>
                      {isOpen ? 'Hide details' : 'View details'}
                    </span>
                    <ChevronDown size={15} />
                  </div>
                </button>

                {isOpen && (
                  <div className="feedback-details">
                    {item.original_query && (
                      <div className="feedback-section">
                        <div className="feedback-label">
                          Original question
                        </div>
                        <div className="feedback-content">
                          {item.original_query}
                        </div>
                      </div>
                    )}

                    {item.original_answer && (
                      <div className="feedback-section">
                        <div className="feedback-label">
                          ASEEL answer
                        </div>
                        <div className="feedback-content">
                          {item.original_answer}
                        </div>
                      </div>
                    )}

                    <div className="feedback-section">
                      <div className="feedback-label">
                        User feedback
                      </div>
                      <div className="feedback-content">
                        {item.message || 'No message provided.'}
                      </div>
                    </div>

                    {(item.city ||
                      item.region ||
                      item.category) && (
                      <div className="feedback-meta">
                        {item.city && (
                          <span>City: {item.city}</span>
                        )}

                        {item.region && (
                          <span>Region: {item.region}</span>
                        )}

                        {item.category && (
                          <span>
                            Category: {item.category}
                          </span>
                        )}
                      </div>
                    )}
                  </div>
                )}

                {canReview && (
                  <div className="feedback-actions">
                    <button
                      type="button"
                      className="btn approve-btn"
                      disabled={updating === item.id}
                      onClick={(event) => {
                        event.stopPropagation();
                        void handleStatus(
                          item.id,
                          'approve',
                        );
                      }}
                    >
                      <Check size={16} />
                      Approve
                    </button>

                    <button
                      type="button"
                      className="btn reject-btn"
                      disabled={updating === item.id}
                      onClick={(event) => {
                        event.stopPropagation();
                        void handleStatus(
                          item.id,
                          'reject',
                        );
                      }}
                    >
                      <X size={16} />
                      Reject
                    </button>
                  </div>
                )}
              </article>
            );
          })}
        </div>
      )}
    </div>
  );
}