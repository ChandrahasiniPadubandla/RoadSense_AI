
import React, { useCallback, useEffect, useMemo, useState } from "react";
import {
  getEmergencyResponses,
  updateEmergencyResponse,
  createEmergencyResponse,
  getAccidents,
  getEmergencyResponders,
} from "../api_services";

const STATUSES = ["ALL", "PENDING", "EN_ROUTE", "ARRIVED", "RESOLVED"];

const STATUS_LABELS = {
  PENDING: "Pending",
  EN_ROUTE: "En Route",
  ARRIVED: "Arrived On Scene",
  RESOLVED: "Resolved",
};

const NOTE_TEMPLATES = [
  "Unit dispatched and proceeding to the location.",
  "Arrived at the scene. Assessing the situation.",
  "First aid and traffic control are in progress.",
  "Patient assistance is being coordinated.",
  "Incident response completed.",
];

const getStatus = (incident) =>
  String(incident?.response_status || "PENDING").toUpperCase();

const getRoadName = (incident) =>
  incident?.accident?.road_name ||
  incident?.road_name ||
  incident?.location ||
  "Unknown Road";

const getResponderName = (incident) =>
  incident?.assigned_user?.name ||
  incident?.assigned_user?.username ||
  incident?.responder_name ||
  "Unassigned";

const formatDate = (value) => {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleString();
};

const statusClass = (status) => {
  const classes = {
    PENDING: "bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300",
    EN_ROUTE: "bg-blue-100 text-blue-800 dark:bg-blue-900/40 dark:text-blue-300",
    ARRIVED: "bg-purple-100 text-purple-800 dark:bg-purple-900/40 dark:text-purple-300",
    RESOLVED: "bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300",
  };
  return classes[status] || "bg-gray-100 text-gray-700 dark:bg-gray-700 dark:text-gray-200";
};

function StatusBadge({ status }) {
  return (
    <span className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${statusClass(status)}`}>
      {STATUS_LABELS[status] || status}
    </span>
  );
}

const inputClass =
  "w-full rounded-lg border border-gray-300 bg-white px-3 py-2.5 text-sm text-gray-900 outline-none placeholder:text-gray-400 focus:border-blue-500 focus:ring-1 focus:ring-blue-500 dark:border-gray-700 dark:bg-gray-800 dark:text-gray-100 dark:placeholder:text-gray-500";

const labelClass =
  "mb-1 block text-sm font-medium text-gray-700 dark:text-gray-300";

const headingClass = "font-semibold text-gray-900 dark:text-gray-100";

const secondaryTextClass = "text-gray-500 dark:text-gray-400";

const templateButtonClass =
  "rounded-full border border-gray-300 px-3 py-1.5 text-xs text-gray-600 hover:bg-gray-50 dark:border-gray-700 dark:text-gray-300 dark:hover:bg-gray-700";

function Modal({ title, onClose, children, wide = false }) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 p-4 backdrop-blur-sm"
      onMouseDown={(event) => {
        if (event.target === event.currentTarget) onClose();
      }}
    >
      <section
        className={`max-h-[90vh] w-full ${
          wide ? "max-w-3xl" : "max-w-xl"
        } overflow-y-auto rounded-xl bg-white shadow-xl dark:bg-gray-900`}
        role="dialog"
        aria-modal="true"
        aria-label={title}
      >
        <div className="sticky top-0 flex items-center justify-between border-b border-gray-200 bg-white px-6 py-4 dark:border-gray-700 dark:bg-gray-900">
          <h2 className="text-lg font-bold text-gray-900 dark:text-gray-100">
            {title}
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg px-3 py-1 text-xl text-gray-500 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-gray-800"
            aria-label="Close modal"
          >
            ×
          </button>
        </div>
        <div className="p-6">{children}</div>
      </section>
    </div>
  );
}

function InfoItem({ label, value }) {
  return (
    <div className="min-w-0">
      <p className="text-xs font-medium uppercase tracking-wide text-gray-500 dark:text-gray-400">
        {label}
      </p>
      <p className="mt-1 break-words text-sm font-medium text-gray-900 dark:text-gray-100">
        {value || "—"}
      </p>
    </div>
  );
}

export default function IncidentsPage() {
  const [incidents, setIncidents] = useState([]);
  const [accidents, setAccidents] = useState([]);
  const [responders, setResponders] = useState([]);

  const [statusFilter, setStatusFilter] = useState("ALL");
  const [searchTerm, setSearchTerm] = useState("");

  const [selectedIncident, setSelectedIncident] = useState(null);
  const [showDispatchModal, setShowDispatchModal] = useState(false);

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const [dispatchForm, setDispatchForm] = useState({
    accident_id: "",
    assigned_user_id: "",
    response_status: "EN_ROUTE",
    notes: "",
  });

  const [editedNotes, setEditedNotes] = useState("");

  const loadIncidents = useCallback(async () => {
    try {
      setError("");
      setLoading(true);
      const data = await getEmergencyResponses();
      setIncidents(Array.isArray(data) ? data : []);
    } catch (err) {
      console.error("Failed to load emergency responses:", err);
      setError(
        err?.response?.data?.detail ||
          err?.message ||
          "Unable to load emergency incidents."
      );
    } finally {
      setLoading(false);
    }
  }, []);

  const loadDispatchOptions = useCallback(async () => {
    try {
      const [accidentData, responderData] = await Promise.all([
        getAccidents(),
        getEmergencyResponders(),
      ]);
      setAccidents(Array.isArray(accidentData) ? accidentData : []);
      setResponders(Array.isArray(responderData) ? responderData : []);
    } catch (err) {
      console.error("Failed to load dispatch options:", err);
      setError(
        err?.response?.data?.detail ||
          err?.message ||
          "Unable to load accidents or responders."
      );
    }
  }, []);

  useEffect(() => {
    loadIncidents();
    loadDispatchOptions();
  }, [loadIncidents, loadDispatchOptions]);

  const counts = useMemo(() => {
    return {
      total: incidents.length,
      enRoute: incidents.filter((item) => getStatus(item) === "EN_ROUTE").length,
      arrived: incidents.filter((item) => getStatus(item) === "ARRIVED").length,
      pending: incidents.filter((item) => getStatus(item) === "PENDING").length,
      resolved: incidents.filter((item) => getStatus(item) === "RESOLVED").length,
    };
  }, [incidents]);

  const filteredIncidents = useMemo(() => {
    const search = searchTerm.trim().toLowerCase();

    return incidents.filter((incident) => {
      const status = getStatus(incident);
      if (statusFilter !== "ALL" && status !== statusFilter) return false;

      const searchableText = [
        getRoadName(incident),
        incident?.notes,
        getResponderName(incident),
        incident?.assigned_user?.email,
        incident?.assigned_user?.phone,
        incident?.accident?.description,
        incident?.response_id,
      ]
        .filter(Boolean)
        .join(" ")
        .toLowerCase();

      return !search || searchableText.includes(search);
    });
  }, [incidents, statusFilter, searchTerm]);

  const openDetails = (incident) => {
    setSelectedIncident(incident);
    setEditedNotes(incident?.notes || "");
    setSuccess("");
    setError("");
  };

  const closeDetails = () => {
    setSelectedIncident(null);
    setEditedNotes("");
  };

  const updateLocalIncident = (updated) => {
    if (!updated?.response_id) return;

    setIncidents((current) =>
      current.map((item) =>
        item.response_id === updated.response_id ? updated : item
      )
    );
    setSelectedIncident(updated);
    setEditedNotes(updated.notes || "");
  };

  const updateStatus = async (nextStatus) => {
    if (!selectedIncident?.response_id || saving) return;

    try {
      setSaving(true);
      setError("");
      setSuccess("");

      const updated = await updateEmergencyResponse(
        selectedIncident.response_id,
        { response_status: nextStatus }
      );

      updateLocalIncident(updated);
      setSuccess(`Status updated to ${STATUS_LABELS[nextStatus]}.`);
    } catch (err) {
      console.error("Status update failed:", err);
      setError(
        err?.response?.data?.detail ||
          err?.message ||
          "Unable to update incident status."
      );
    } finally {
      setSaving(false);
    }
  };

  const saveNotes = async () => {
    if (!selectedIncident?.response_id || saving) return;

    try {
      setSaving(true);
      setError("");
      setSuccess("");

      const updated = await updateEmergencyResponse(
        selectedIncident.response_id,
        { notes: editedNotes }
      );

      updateLocalIncident(updated);
      setSuccess("Incident notes saved.");
    } catch (err) {
      console.error("Saving notes failed:", err);
      setError(
        err?.response?.data?.detail ||
          err?.message ||
          "Unable to save notes."
      );
    } finally {
      setSaving(false);
    }
  };

  const openDispatch = () => {
    setDispatchForm({
      accident_id: "",
      assigned_user_id: "",
      response_status: "EN_ROUTE",
      notes: "",
    });
    setError("");
    setSuccess("");
    setShowDispatchModal(true);
  };

  const submitDispatch = async (event) => {
    event.preventDefault();

    if (!dispatchForm.accident_id) {
      setError("Please select an accident.");
      return;
    }

    try {
      setSaving(true);
      setError("");
      setSuccess("");

      const payload = {
        accident_id: dispatchForm.accident_id,
        assigned_user_id: dispatchForm.assigned_user_id || null,
        response_status: dispatchForm.response_status,
        notes: dispatchForm.notes.trim() || null,
      };

      await createEmergencyResponse(payload);
      setShowDispatchModal(false);
      setSuccess("Emergency response dispatched successfully.");
      await loadIncidents();
    } catch (err) {
      console.error("Dispatch failed:", err);
      setError(
        err?.response?.data?.detail ||
          err?.message ||
          "Unable to dispatch emergency response."
      );
    } finally {
      setSaving(false);
    }
  };

  const appendTemplate = (template) => {
    setEditedNotes((current) =>
      current.trim() ? `${current.trim()}\n${template}` : template
    );
  };

  const currentStatus = selectedIncident
    ? getStatus(selectedIncident)
    : "";

  const accident = selectedIncident?.accident || {};
  const responder = selectedIncident?.assigned_user || {};

  const cards = [
    { label: "Total Incidents", value: counts.total, color: "border-gray-400" },
    { label: "En Route", value: counts.enRoute, color: "border-blue-500" },
    { label: "Arrived On Scene", value: counts.arrived, color: "border-purple-500" },
    { label: "Pending", value: counts.pending, color: "border-amber-500" },
    { label: "Resolved", value: counts.resolved, color: "border-green-500" },
  ];

  return (
    <main className="space-y-6 p-4 text-gray-900 dark:text-gray-100 md:p-6">
      {/* Page heading */}
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">
            Incident Details Log
          </h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Monitor emergency responses, dispatch units, and update incident progress.
          </p>
        </div>

        <button
          type="button"
          onClick={openDispatch}
          className="rounded-lg bg-blue-600 px-5 py-2.5 text-sm font-semibold text-white hover:bg-blue-700"
        >
          + Dispatch Unit
        </button>
      </div>

      {/* Feedback messages */}
      {error && (
        <div className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900 dark:bg-red-950/40 dark:text-red-300">
          {error}
        </div>
      )}

      {success && (
        <div className="rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-700 dark:border-green-900 dark:bg-green-950/40 dark:text-green-300">
          {success}
        </div>
      )}

      {/* KPI cards */}
      <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
        {cards.map((card) => (
          <div
            key={card.label}
            className={`rounded-xl border border-l-4 ${card.color} bg-white p-4 shadow-sm dark:bg-gray-900`}
          >
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {card.label}
            </p>
            <p className="mt-2 text-2xl font-bold text-gray-900 dark:text-gray-100">
              {card.value}
            </p>
          </div>
        ))}
      </section>

      {/* Filters and search */}
      <section className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm dark:border-gray-700 dark:bg-gray-900">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="flex flex-wrap gap-2">
            {STATUSES.map((status) => (
              <button
                key={status}
                type="button"
                onClick={() => setStatusFilter(status)}
                className={`rounded-lg px-3 py-2 text-xs font-semibold transition ${
                  statusFilter === status
                    ? "bg-blue-600 text-white"
                    : "bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-gray-800 dark:text-gray-300 dark:hover:bg-gray-700"
                }`}
              >
                {status === "ALL" ? "All" : STATUS_LABELS[status]}
              </button>
            ))}
          </div>

          <input
            type="search"
            value={searchTerm}
            onChange={(event) => setSearchTerm(event.target.value)}
            placeholder="Search road, notes, responder..."
            className={`${inputClass} lg:max-w-sm`}
          />
        </div>
      </section>

      {/* Incident table */}
      <section className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm dark:border-gray-700 dark:bg-gray-900">
        <div className="flex items-center justify-between border-b border-gray-200 px-5 py-4 dark:border-gray-700">
          <h2 className={headingClass}>Emergency Responses</h2>

          <button
            type="button"
            onClick={loadIncidents}
            disabled={loading}
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 disabled:opacity-50 dark:border-gray-700 dark:text-gray-300 dark:hover:bg-gray-800"
          >
            {loading ? "Refreshing..." : "Refresh"}
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full min-w-[850px] text-left text-sm">
            <thead className="bg-gray-50 text-xs uppercase text-gray-500 dark:bg-gray-800 dark:text-gray-300">
              <tr>
                <th className="px-5 py-3">Road / Location</th>
                <th className="px-5 py-3">Severity</th>
                <th className="px-5 py-3">Casualties</th>
                <th className="px-5 py-3">Responder</th>
                <th className="px-5 py-3">Status</th>
                <th className="px-5 py-3">Assigned At</th>
                <th className="px-5 py-3">Details</th>
              </tr>
            </thead>

            <tbody className="divide-y divide-gray-200 dark:divide-gray-700">
              {loading ? (
                <tr>
                  <td colSpan="7" className="px-5 py-10 text-center text-gray-500 dark:text-gray-400">
                    Loading incidents...
                  </td>
                </tr>
              ) : filteredIncidents.length === 0 ? (
                <tr>
                  <td colSpan="7" className="px-5 py-10 text-center text-gray-500 dark:text-gray-400">
                    No incidents found.
                  </td>
                </tr>
              ) : (
                filteredIncidents.map((incident) => {
                  const status = getStatus(incident);
                  const injuries = incident?.accident?.injuries ?? 0;
                  const fatalities = incident?.accident?.fatalities ?? 0;

                  return (
                    <tr
                      key={incident.response_id}
                      onClick={() => openDetails(incident)}
                      className="cursor-pointer bg-white transition-colors hover:bg-blue-50/50 dark:bg-gray-900 dark:hover:bg-gray-800"
                    >
                      <td className="px-5 py-4 font-medium text-gray-900 dark:text-gray-100">
                        {getRoadName(incident)}
                        <p className="mt-1 max-w-xs truncate text-xs font-normal text-gray-500 dark:text-gray-400">
                          {incident?.accident?.description || "No description"}
                        </p>
                      </td>

                      <td className="px-5 py-4 text-gray-700 dark:text-gray-300">
                        {incident?.accident?.severity || "—"}
                      </td>

                      <td className="px-5 py-4">
                        <span className="text-red-600 dark:text-red-400">
                          {fatalities} fatalities
                        </span>
                        <span className="block text-xs text-gray-500 dark:text-gray-400">
                          {injuries} injuries
                        </span>
                      </td>

                      <td className="px-5 py-4 font-medium text-gray-800 dark:text-gray-100">
                        {getResponderName(incident)}
                      </td>

                      <td className="px-5 py-4">
                        <StatusBadge status={status} />
                      </td>

                      <td className="px-5 py-4 text-gray-600 dark:text-gray-300">
                        {formatDate(incident.assigned_at)}
                      </td>

                      <td className="px-5 py-4">
                        <button
                          type="button"
                          onClick={(event) => {
                            event.stopPropagation();
                            openDetails(incident);
                          }}
                          className="rounded-lg border border-gray-300 px-3 py-1.5 text-xs font-semibold text-blue-700 hover:bg-blue-50 dark:border-gray-700 dark:text-blue-300 dark:hover:bg-gray-800"
                        >
                          View Log
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </section>

      {/* Incident details modal */}
      {selectedIncident && (
        <Modal title="Incident Details" onClose={closeDetails} wide>
          <div className="space-y-6">
            {/* Accident context */}
            <section>
              <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                <h3 className={headingClass}>Accident Context</h3>
                <StatusBadge status={currentStatus} />
              </div>

              <div className="grid grid-cols-1 gap-4 rounded-lg bg-gray-50 p-4 dark:bg-gray-800 sm:grid-cols-2">
                <InfoItem label="Road / Location" value={getRoadName(selectedIncident)} />
                <InfoItem label="Severity" value={accident.severity || "—"} />
                <InfoItem label="Accident Date" value={formatDate(accident.accident_datetime)} />
                <InfoItem label="Response Assigned" value={formatDate(selectedIncident.assigned_at)} />
                <div className="sm:col-span-2">
                  <InfoItem
                    label="Accident Description"
                    value={accident.description || "No description provided"}
                  />
                </div>
              </div>
            </section>

            {/* Casualty stats */}
            <section>
              <h3 className={`${headingClass} mb-3`}>Casualty Statistics</h3>
              <div className="grid grid-cols-2 gap-3">
                <div className="rounded-lg border border-red-200 bg-red-50 p-4 dark:border-red-900 dark:bg-red-950/30">
                  <p className="text-sm text-red-700 dark:text-red-300">Fatalities</p>
                  <p className="mt-1 text-2xl font-bold text-red-800 dark:text-red-200">
                    {accident.fatalities ?? 0}
                  </p>
                </div>

                <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 dark:border-amber-900 dark:bg-amber-950/30">
                  <p className="text-sm text-amber-700 dark:text-amber-300">Injuries</p>
                  <p className="mt-1 text-2xl font-bold text-amber-800 dark:text-amber-200">
                    {accident.injuries ?? 0}
                  </p>
                </div>
              </div>
            </section>

            {/* Responder contact */}
            <section>
              <h3 className={`${headingClass} mb-3`}>Assigned Responder</h3>
              <div className="grid grid-cols-1 gap-4 rounded-lg border border-gray-200 p-4 dark:border-gray-700 sm:grid-cols-2">
                <InfoItem label="Name" value={responder.name || responder.username || "Unassigned"} />
                <InfoItem label="Role" value={responder.role_name || "—"} />
                <InfoItem label="Phone" value={responder.phone || "Not available"} />
                <InfoItem label="Email" value={responder.email || "Not available"} />
              </div>
            </section>

            {/* Status progression */}
            <section>
              <h3 className={`${headingClass} mb-3`}>Response Progress</h3>

              <div className="mb-4 flex flex-wrap items-center gap-2">
                {["EN_ROUTE", "ARRIVED", "RESOLVED"].map((status, index) => {
                  const order = {
                    PENDING: 0,
                    EN_ROUTE: 1,
                    ARRIVED: 2,
                    RESOLVED: 3,
                  };
                  const completed = order[currentStatus] >= index + 1;

                  return (
                    <React.Fragment key={status}>
                      {index > 0 && (
                        <span className="text-gray-300 dark:text-gray-600">→</span>
                      )}
                      <span
                        className={`rounded-full px-3 py-1 text-xs font-semibold ${
                          completed
                            ? "bg-green-100 text-green-800 dark:bg-green-900/40 dark:text-green-300"
                            : "bg-gray-100 text-gray-500 dark:bg-gray-800 dark:text-gray-400"
                        }`}
                      >
                        {STATUS_LABELS[status]}
                      </span>
                    </React.Fragment>
                  );
                })}
              </div>

              <div className="flex flex-wrap gap-2">
                {currentStatus === "PENDING" && (
                  <button
                    type="button"
                    disabled={saving}
                    onClick={() => updateStatus("EN_ROUTE")}
                    className="rounded-lg bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50"
                  >
                    {saving ? "Updating..." : "Mark En Route"}
                  </button>
                )}

                {currentStatus === "EN_ROUTE" && (
                  <button
                    type="button"
                    disabled={saving}
                    onClick={() => updateStatus("ARRIVED")}
                    className="rounded-lg bg-purple-600 px-4 py-2 text-sm font-semibold text-white hover:bg-purple-700 disabled:opacity-50"
                  >
                    {saving ? "Updating..." : "Mark Arrived On Scene"}
                  </button>
                )}

                {currentStatus === "ARRIVED" && (
                  <button
                    type="button"
                    disabled={saving}
                    onClick={() => updateStatus("RESOLVED")}
                    className="rounded-lg bg-green-600 px-4 py-2 text-sm font-semibold text-white hover:bg-green-700 disabled:opacity-50"
                  >
                    {saving ? "Updating..." : "Mark Resolved"}
                  </button>
                )}

                {currentStatus === "RESOLVED" && (
                  <span className="rounded-lg bg-green-50 px-4 py-2 text-sm font-semibold text-green-700 dark:bg-green-900/30 dark:text-green-300">
                    Incident resolved
                  </span>
                )}
              </div>

              <div className="mt-4 grid grid-cols-1 gap-3 text-sm sm:grid-cols-3">
                <InfoItem label="Assigned At" value={formatDate(selectedIncident.assigned_at)} />
                <InfoItem label="Arrived At" value={formatDate(selectedIncident.arrived_at)} />
                <InfoItem label="Resolved At" value={formatDate(selectedIncident.resolved_at)} />
              </div>
            </section>

            {/* Editable notes */}
            <section>
              <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                <h3 className={headingClass}>On-Scene Notes</h3>
                <span className="text-xs text-gray-500 dark:text-gray-400">
                  Notes are saved to this emergency response.
                </span>
              </div>

              <textarea
                value={editedNotes}
                onChange={(event) => setEditedNotes(event.target.value)}
                rows={5}
                placeholder="Enter observations, actions taken, or updates from the scene..."
                className={inputClass}
              />

              <div className="mt-3 flex flex-wrap gap-2">
                {NOTE_TEMPLATES.map((template) => (
                  <button
                    key={template}
                    type="button"
                    onClick={() => appendTemplate(template)}
                    className={templateButtonClass}
                  >
                    + {template}
                  </button>
                ))}
              </div>

              <div className="mt-4 flex justify-end">
                <button
                  type="button"
                  onClick={saveNotes}
                  disabled={saving}
                  className="rounded-lg bg-gray-900 px-5 py-2.5 text-sm font-semibold text-white hover:bg-black disabled:opacity-50 dark:bg-blue-600 dark:hover:bg-blue-700"
                >
                  {saving ? "Saving..." : "Save Notes"}
                </button>
              </div>
            </section>
          </div>
        </Modal>
      )}

      {/* Dispatch modal */}
      {showDispatchModal && (
        <Modal
          title="Dispatch Emergency Unit"
          onClose={() => setShowDispatchModal(false)}
        >
          <form onSubmit={submitDispatch} className="space-y-4">
            <div>
              <label className={labelClass}>Select Accident *</label>
              <select
                required
                value={dispatchForm.accident_id}
                onChange={(event) =>
                  setDispatchForm((current) => ({
                    ...current,
                    accident_id: event.target.value,
                  }))
                }
                className={inputClass}
              >
                <option value="">Choose an accident</option>
                {accidents.map((item) => {
                  const id = item.accident_id || item.id;
                  const road =
                    item.road_name ||
                    item.road?.road_name ||
                    item.location ||
                    "Unknown Road";

                  return (
                    <option key={id} value={id}>
                      {road} — {item.severity || "Severity unknown"}
                    </option>
                  );
                })}
              </select>
            </div>

            <div>
              <label className={labelClass}>Assign Responder</label>
              <select
                value={dispatchForm.assigned_user_id}
                onChange={(event) =>
                  setDispatchForm((current) => ({
                    ...current,
                    assigned_user_id: event.target.value,
                  }))
                }
                className={inputClass}
              >
                <option value="">Unassigned</option>
                {responders.map((responder) => (
                  <option key={responder.user_id} value={responder.user_id}>
                    {responder.name || responder.username}
                    {responder.role_name ? ` (${responder.role_name})` : ""}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <label className={labelClass}>Initial Status</label>
              <select
                value={dispatchForm.response_status}
                onChange={(event) =>
                  setDispatchForm((current) => ({
                    ...current,
                    response_status: event.target.value,
                  }))
                }
                className={inputClass}
              >
                <option value="PENDING">Pending</option>
                <option value="EN_ROUTE">En Route</option>
              </select>
            </div>

            <div>
              <label className={labelClass}>Operational Notes</label>
              <textarea
                rows={4}
                value={dispatchForm.notes}
                onChange={(event) =>
                  setDispatchForm((current) => ({
                    ...current,
                    notes: event.target.value,
                  }))
                }
                placeholder="Add dispatch instructions or details..."
                className={inputClass}
              />

              <div className="mt-2 flex flex-wrap gap-2">
                {NOTE_TEMPLATES.slice(0, 3).map((template) => (
                  <button
                    key={template}
                    type="button"
                    onClick={() =>
                      setDispatchForm((current) => ({
                        ...current,
                        notes: current.notes.trim()
                          ? `${current.notes.trim()}\n${template}`
                          : template,
                      }))
                    }
                    className={templateButtonClass}
                  >
                    + {template}
                  </button>
                ))}
              </div>
            </div>

            <div className="flex justify-end gap-2 border-t border-gray-200 pt-4 dark:border-gray-700">
              <button
                type="button"
                onClick={() => setShowDispatchModal(false)}
                className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-gray-700 dark:text-gray-300 dark:hover:bg-gray-800"
              >
                Cancel
              </button>

              <button
                type="submit"
                disabled={saving}
                className="rounded-lg bg-blue-600 px-5 py-2 text-sm font-semibold text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {saving ? "Dispatching..." : "Dispatch Unit"}
              </button>
            </div>
          </form>
        </Modal>
      )}
    </main>
  );
}
 