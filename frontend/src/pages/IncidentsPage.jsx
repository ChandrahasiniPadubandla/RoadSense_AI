import React, {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from "react";
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

// Set to false if your backend allows several responses for one accident.
const ONE_RESPONSE_PER_ACCIDENT = true;

const labelClass =
  "mb-1 block text-sm font-medium text-gray-700 dark:text-gray-200";

const inputClass =
  "w-full rounded-lg border border-gray-300 bg-white px-3 py-2.5 text-sm text-gray-900 outline-none focus:border-blue-500 dark:border-slate-600 dark:bg-slate-800 dark:text-white dark:placeholder-gray-400";

// Works whether api_services returns the body or a full axios response.
const unwrap = (res) => res?.data ?? res;

// <select> values are always strings; send numbers when the id is numeric.
const toId = (value) =>
  value !== "" && value != null && !Number.isNaN(Number(value))
    ? Number(value)
    : value;

const getErrorMessage = (err, fallback) =>
  err?.response?.data?.detail || err?.message || fallback;

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

const getIncidentAccidentId = (incident) =>
  incident?.accident?.accident_id ??
  incident?.accident?.id ??
  incident?.accident_id;

const formatDate = (value) => {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return date.toLocaleString();
};

const statusClass = (status) => {
  const classes = {
    PENDING: "bg-amber-100 text-amber-800",
    EN_ROUTE: "bg-blue-100 text-blue-800",
    ARRIVED: "bg-purple-100 text-purple-800",
    RESOLVED: "bg-green-100 text-green-800",
  };
  return classes[status] || "bg-gray-100 text-gray-700";
};

// Supports different response formats returned by the API.
const normalizeList = (response, keys = []) => {
  if (Array.isArray(response)) return response;

  if (Array.isArray(response?.data)) return response.data;

  for (const key of keys) {
    if (Array.isArray(response?.[key])) return response[key];
    if (Array.isArray(response?.data?.[key])) {
      return response.data[key];
    }
  }

  return [];
};

// Handles role names represented as strings or objects.
const getRoleName = (responder) => {
  const role =
    responder?.role_name ??
    responder?.user_role ??
    responder?.role?.name ??
    responder?.role?.role_name ??
    responder?.role ??
    "";

  if (typeof role === "string") return role.toLowerCase();

  if (Array.isArray(role)) {
    return role
      .map((item) =>
        typeof item === "string"
          ? item
          : item?.name || item?.role_name || ""
      )
      .join(" ")
      .toLowerCase();
  }

  return "";
};

const isEmergencyResponder = (responder) => {
  const role = getRoleName(responder).replace(/[\s_-]/g, "");

  return (
    role.includes("emergencyresponder") ||
    role.includes("emergencyresponse") ||
    role === "responder"
  );
};

function StatusBadge({ status }) {
  return (
    <span
      className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${statusClass(
        status
      )}`}
    >
      {STATUS_LABELS[status] || status}
    </span>
  );
}

// Shown inside modals so messages are not hidden behind the overlay.
function Feedback({ error, success }) {
  if (!error && !success) return null;

  return (
    <div
      role={error ? "alert" : "status"}
      className={`mb-4 rounded-lg border px-4 py-3 text-sm ${
        error
          ? "border-red-200 bg-red-50 text-red-700 dark:border-red-900 dark:bg-red-950/40 dark:text-red-300"
          : "border-green-200 bg-green-50 text-green-700 dark:border-green-900 dark:bg-green-950/40 dark:text-green-300"
      }`}
    >
      {error || success}
    </div>
  );
}

function Modal({
  title,
  onClose,
  children,
  wide = false,
  error = "",
  success = "",
}) {
  // Close on Escape.
  useEffect(() => {
    const handleKey = (event) => {
      if (event.key === "Escape") onClose();
    };
    window.addEventListener("keydown", handleKey);
    return () => window.removeEventListener("keydown", handleKey);
  }, [onClose]);

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
        } overflow-y-auto rounded-xl bg-white text-gray-900 shadow-xl dark:bg-slate-900 dark:text-white`}
        role="dialog"
        aria-modal="true"
        aria-label={title}
      >
        <div className="sticky top-0 flex items-center justify-between border-b border-gray-200 bg-white px-6 py-4 dark:border-slate-700 dark:bg-slate-900">
          <h2 className="text-lg font-bold text-gray-900 dark:text-white">
            {title}
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg px-3 py-1 text-xl text-gray-500 hover:bg-gray-100 dark:text-gray-300 dark:hover:bg-slate-800"
            aria-label="Close modal"
          >
            ×
          </button>
        </div>
        <div className="p-6">
          <Feedback error={error} success={success} />
          {children}
        </div>
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
  const [optionsLoading, setOptionsLoading] = useState(false);
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

  const modalOpen = !!selectedIncident || showDispatchModal;

  // Load emergency response records.
  const loadIncidents = useCallback(async () => {
    try {
      setError("");
      setLoading(true);

      const response = await getEmergencyResponses();
      const data = normalizeList(response, [
        "incidents",
        "responses",
        "results",
      ]);

      setIncidents(data);
    } catch (err) {
      console.error("Failed to load emergency responses:", err);
      setError(getErrorMessage(err, "Unable to load emergency incidents."));
    } finally {
      setLoading(false);
    }
  }, []);

  // Load accidents and responders for the dispatch form.
  const loadDispatchOptions = useCallback(async () => {
    try {
      setOptionsLoading(true);

      const [accidentResponse, responderResponse] = await Promise.all([
        getAccidents(),
        getEmergencyResponders(),
      ]);

      const accidentData = normalizeList(accidentResponse, [
        "accidents",
        "results",
      ]);

      const responderData = normalizeList(responderResponse, [
        "responders",
        "users",
        "results",
      ]);

      setAccidents(accidentData);
      setResponders(responderData.filter(isEmergencyResponder));
    } catch (err) {
      console.error("Failed to load dispatch options:", err);
      setError(
        getErrorMessage(err, "Unable to load accidents or responders.")
      );
    } finally {
      setOptionsLoading(false);
    }
  }, []);

  useEffect(() => {
    loadIncidents();
    loadDispatchOptions();
  }, [loadIncidents, loadDispatchOptions]);

  // Dashboard totals.
  const counts = useMemo(
    () => ({
      total: incidents.length,
      enRoute: incidents.filter((item) => getStatus(item) === "EN_ROUTE")
        .length,
      arrived: incidents.filter((item) => getStatus(item) === "ARRIVED")
        .length,
      pending: incidents.filter((item) => getStatus(item) === "PENDING")
        .length,
      resolved: incidents.filter((item) => getStatus(item) === "RESOLVED")
        .length,
    }),
    [incidents]
  );

  // Status and search filters.
  const filteredIncidents = useMemo(() => {
    const search = searchTerm.trim().toLowerCase();

    return incidents.filter((incident) => {
      const status = getStatus(incident);

      if (statusFilter !== "ALL" && status !== statusFilter) {
        return false;
      }

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

  // Accidents that do not have an emergency response yet.
  const availableAccidents = useMemo(() => {
    if (!ONE_RESPONSE_PER_ACCIDENT) return accidents;

    const dispatchedIds = new Set(
      incidents
        .map(getIncidentAccidentId)
        .filter((id) => id != null)
        .map(String)
    );

    return accidents.filter((item) => {
      const id = item.accident_id ?? item.id;
      return id != null && !dispatchedIds.has(String(id));
    });
  }, [accidents, incidents]);

  const openDetails = (incident) => {
    setSelectedIncident(incident);
    setEditedNotes(incident?.notes || "");
    setSuccess("");
    setError("");
  };

  const closeDetails = useCallback(() => {
    setSelectedIncident(null);
    setEditedNotes("");
    setError("");
    setSuccess("");
  }, []);

  const closeDispatch = useCallback(() => {
    setShowDispatchModal(false);
    setError("");
  }, []);

  // Merge changes into the table row and the open modal so nested data
  // (accident, assigned_user) is kept when the API returns a partial record.
  const updateLocalIncident = (changes) => {
    const id = changes?.response_id ?? selectedIncident?.response_id;
    if (id == null) return;

    setIncidents((current) =>
      current.map((item) =>
        item.response_id === id ? { ...item, ...changes } : item
      )
    );

    setSelectedIncident((current) =>
      current ? { ...current, ...changes } : current
    );
  };

  // Update incident status.
  const updateStatus = async (nextStatus) => {
    if (!selectedIncident?.response_id || saving) return;

    try {
      setSaving(true);
      setError("");
      setSuccess("");

      const updated = unwrap(
        await updateEmergencyResponse(selectedIncident.response_id, {
          response_status: nextStatus,
        })
      );

      updateLocalIncident({
        response_status: nextStatus,
        ...(updated && typeof updated === "object" ? updated : {}),
      });
      setSuccess(`Status updated to ${STATUS_LABELS[nextStatus]}.`);
    } catch (err) {
      console.error("Status update failed:", err);
      setError(getErrorMessage(err, "Unable to update incident status."));
    } finally {
      setSaving(false);
    }
  };

  // Save edited notes.
  const saveNotes = async () => {
    if (!selectedIncident?.response_id || saving) return;

    try {
      setSaving(true);
      setError("");
      setSuccess("");

      const updated = unwrap(
        await updateEmergencyResponse(selectedIncident.response_id, {
          notes: editedNotes,
        })
      );

      const merged = {
        notes: editedNotes,
        ...(updated && typeof updated === "object" ? updated : {}),
      };

      updateLocalIncident(merged);
      setEditedNotes(merged.notes ?? editedNotes);
      setSuccess("Incident notes saved.");
    } catch (err) {
      console.error("Saving notes failed:", err);
      setError(getErrorMessage(err, "Unable to save notes."));
    } finally {
      setSaving(false);
    }
  };

  // Open the dispatch form and refresh its options.
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
    loadDispatchOptions();
  };

  // Create a new emergency response.
  const submitDispatch = async (event) => {
    event.preventDefault();

    if (saving) return;

    if (!dispatchForm.accident_id) {
      setError("Please select an accident.");
      return;
    }

    try {
      setSaving(true);
      setError("");
      setSuccess("");

      const payload = {
        accident_id: toId(dispatchForm.accident_id),
        assigned_user_id: dispatchForm.assigned_user_id
          ? toId(dispatchForm.assigned_user_id)
          : null,
        response_status: dispatchForm.response_status,
        notes: dispatchForm.notes.trim() || null,
      };

      await createEmergencyResponse(payload);

      setShowDispatchModal(false);
      setSuccess("Emergency response dispatched successfully.");

      await loadIncidents();
    } catch (err) {
      console.error("Dispatch failed:", err);
      setError(getErrorMessage(err, "Unable to dispatch emergency response."));
    } finally {
      setSaving(false);
    }
  };

  const appendTemplate = (template) => {
    setEditedNotes((current) =>
      current.trim() ? `${current.trim()}\n${template}` : template
    );
  };

  const currentStatus = selectedIncident ? getStatus(selectedIncident) : "";

  const accident = selectedIncident?.accident || {};
  const responder = selectedIncident?.assigned_user || {};

  const cards = [
    {
      label: "Total Incidents",
      value: counts.total,
      color: "border-gray-400",
    },
    {
      label: "En Route",
      value: counts.enRoute,
      color: "border-blue-500",
    },
    {
      label: "Arrived On Scene",
      value: counts.arrived,
      color: "border-purple-500",
    },
    {
      label: "Pending",
      value: counts.pending,
      color: "border-amber-500",
    },
    {
      label: "Resolved",
      value: counts.resolved,
      color: "border-green-500",
    },
  ];

  return (
    <main className="space-y-6 p-4 text-gray-900 dark:text-gray-100 md:p-6">
      {/* Page heading */}
      <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
            Incident Details Log
          </h1>
          <p className="mt-1 text-sm text-gray-500 dark:text-gray-400">
            Monitor emergency responses, dispatch units, and update incident
            progress.
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

      {/* Feedback messages (hidden while a modal is open; modals show their own) */}
      {!modalOpen && error && (
        <div
          role="alert"
          className="rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700 dark:border-red-900 dark:bg-red-950/40 dark:text-red-300"
        >
          {error}
        </div>
      )}

      {!modalOpen && success && (
        <div
          role="status"
          className="rounded-lg border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-700 dark:border-green-900 dark:bg-green-950/40 dark:text-green-300"
        >
          {success}
        </div>
      )}

      {/* KPI cards */}
      <section className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-5">
        {cards.map((card) => (
          <div
            key={card.label}
            className={`rounded-xl border border-l-4 ${card.color} bg-white p-4 shadow-sm dark:border-t-slate-700 dark:border-r-slate-700 dark:border-b-slate-700 dark:bg-slate-900`}
          >
            <p className="text-sm text-gray-500 dark:text-gray-400">
              {card.label}
            </p>
            <p className="mt-2 text-2xl font-bold text-gray-900 dark:text-white">
              {card.value}
            </p>
          </div>
        ))}
      </section>

      {/* Filters and search */}
      <section className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm dark:border-slate-700 dark:bg-slate-900">
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
                    : "bg-gray-100 text-gray-600 hover:bg-gray-200 dark:bg-slate-800 dark:text-gray-300 dark:hover:bg-slate-700"
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
            aria-label="Search incidents"
            className={`${inputClass} lg:max-w-sm`}
          />
        </div>
      </section>

      {/* Incident table */}
      <section className="overflow-hidden rounded-xl border border-gray-200 bg-white shadow-sm dark:border-slate-700 dark:bg-slate-900">
        <div className="flex items-center justify-between border-b border-gray-200 px-5 py-4 dark:border-slate-700">
          <h2 className="font-semibold text-gray-900 dark:text-white">
            Emergency Responses
          </h2>

          <button
            type="button"
            onClick={loadIncidents}
            disabled={loading}
            className="rounded-lg border border-gray-300 px-3 py-2 text-sm text-gray-700 hover:bg-gray-50 disabled:opacity-50 dark:border-slate-600 dark:text-gray-200 dark:hover:bg-slate-800"
          >
            {loading ? "Refreshing..." : "Refresh"}
          </button>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full min-w-[850px] text-left text-sm">
            <thead className="bg-gray-50 text-xs uppercase text-gray-500 dark:bg-slate-800 dark:text-gray-300">
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

            <tbody className="divide-y divide-gray-200 dark:divide-slate-700">
              {loading ? (
                <tr>
                  <td
                    colSpan={7}
                    className="px-5 py-10 text-center text-gray-500 dark:text-gray-400"
                  >
                    Loading incidents...
                  </td>
                </tr>
              ) : filteredIncidents.length === 0 ? (
                <tr>
                  <td
                    colSpan={7}
                    className="px-5 py-10 text-center text-gray-500 dark:text-gray-400"
                  >
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
                      className="cursor-pointer hover:bg-blue-50/50 dark:hover:bg-slate-800"
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

                      <td className="px-5 py-4 text-gray-700 dark:text-gray-300">
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
                          className="rounded-lg border border-gray-300 px-3 py-1.5 text-xs font-semibold text-blue-700 hover:bg-blue-50 dark:border-slate-600 dark:text-blue-400 dark:hover:bg-slate-800"
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
        <Modal
          title="Incident Details"
          onClose={closeDetails}
          error={error}
          success={success}
          wide
        >
          <div className="space-y-6">
            {/* Accident context */}
            <section>
              <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                <h3 className="font-semibold text-gray-900 dark:text-white">
                  Accident Context
                </h3>
                <StatusBadge status={currentStatus} />
              </div>

              <div className="grid grid-cols-1 gap-4 rounded-lg bg-gray-50 p-4 dark:bg-slate-800 sm:grid-cols-2">
                <InfoItem
                  label="Road / Location"
                  value={getRoadName(selectedIncident)}
                />
                <InfoItem label="Severity" value={accident.severity || "—"} />
                <InfoItem
                  label="Accident Date"
                  value={formatDate(accident.accident_datetime)}
                />
                <InfoItem
                  label="Response Assigned"
                  value={formatDate(selectedIncident.assigned_at)}
                />
                <div className="sm:col-span-2">
                  <InfoItem
                    label="Accident Description"
                    value={accident.description || "No description provided"}
                  />
                </div>
              </div>
            </section>

            {/* Casualty statistics */}
            <section>
              <h3 className="mb-3 font-semibold text-gray-900 dark:text-white">
                Casualty Statistics
              </h3>

              <div className="grid grid-cols-2 gap-3">
                <div className="rounded-lg border border-red-200 bg-red-50 p-4 dark:border-red-900 dark:bg-red-950/30">
                  <p className="text-sm text-red-700 dark:text-red-300">
                    Fatalities
                  </p>
                  <p className="mt-1 text-2xl font-bold text-red-800 dark:text-red-200">
                    {accident.fatalities ?? 0}
                  </p>
                </div>

                <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 dark:border-amber-900 dark:bg-amber-950/30">
                  <p className="text-sm text-amber-700 dark:text-amber-300">
                    Injuries
                  </p>
                  <p className="mt-1 text-2xl font-bold text-amber-800 dark:text-amber-200">
                    {accident.injuries ?? 0}
                  </p>
                </div>
              </div>
            </section>

            {/* Responder contact */}
            <section>
              <h3 className="mb-3 font-semibold text-gray-900 dark:text-white">
                Assigned Responder
              </h3>

              <div className="grid grid-cols-1 gap-4 rounded-lg border border-gray-200 p-4 dark:border-slate-700 sm:grid-cols-2">
                <InfoItem
                  label="Name"
                  value={responder.name || responder.username || "Unassigned"}
                />
                <InfoItem
                  label="Role"
                  value={responder.role_name || responder.role?.name || "—"}
                />
                <InfoItem
                  label="Phone"
                  value={responder.phone || "Not available"}
                />
                <InfoItem
                  label="Email"
                  value={responder.email || "Not available"}
                />
              </div>
            </section>

            {/* Status progression */}
            <section>
              <h3 className="mb-3 font-semibold text-gray-900 dark:text-white">
                Response Progress
              </h3>

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
                        <span className="text-gray-300 dark:text-gray-600">
                          →
                        </span>
                      )}
                      <span
                        className={`rounded-full px-3 py-1 text-xs font-semibold ${
                          completed
                            ? "bg-green-100 text-green-800"
                            : "bg-gray-100 text-gray-500 dark:bg-slate-800 dark:text-gray-400"
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
                  <span className="rounded-lg bg-green-50 px-4 py-2 text-sm font-semibold text-green-700 dark:bg-green-950/40 dark:text-green-300">
                    Incident resolved
                  </span>
                )}
              </div>

              <div className="mt-4 grid grid-cols-1 gap-3 text-sm sm:grid-cols-3">
                <InfoItem
                  label="Assigned At"
                  value={formatDate(selectedIncident.assigned_at)}
                />
                <InfoItem
                  label="Arrived At"
                  value={formatDate(selectedIncident.arrived_at)}
                />
                <InfoItem
                  label="Resolved At"
                  value={formatDate(selectedIncident.resolved_at)}
                />
              </div>
            </section>

            {/* Editable notes */}
            <section>
              <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
                <label
                  htmlFor="incident-notes"
                  className="font-semibold text-gray-900 dark:text-white"
                >
                  On-Scene Notes
                </label>
                <span className="text-xs text-gray-500 dark:text-gray-400">
                  Notes are saved to this emergency response.
                </span>
              </div>

              <textarea
                id="incident-notes"
                value={editedNotes}
                onChange={(event) => setEditedNotes(event.target.value)}
                rows={5}
                placeholder="Enter observations, actions taken, or updates from the scene..."
                className={`${inputClass} resize-y`}
              />

              <div className="mt-3 flex flex-wrap gap-2">
                {NOTE_TEMPLATES.map((template) => (
                  <button
                    key={template}
                    type="button"
                    onClick={() => appendTemplate(template)}
                    className="rounded-full border border-gray-300 px-3 py-1.5 text-xs text-gray-600 hover:bg-gray-50 dark:border-slate-600 dark:text-gray-300 dark:hover:bg-slate-800"
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
          onClose={closeDispatch}
          error={error}
          success={success}
        >
          <form onSubmit={submitDispatch} className="space-y-4">
            {/* Select accident */}
            <div>
              <label htmlFor="dispatch-accident" className={labelClass}>
                Select Accident *
              </label>

              <select
                id="dispatch-accident"
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
                <option value="">
                  {availableAccidents.length === 0 && !optionsLoading
                    ? "No accidents awaiting dispatch"
                    : "Choose an accident"}
                </option>

                {availableAccidents.map((item) => {
                  const id = item.accident_id ?? item.id;
                  if (id == null) return null;

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

            {/* Assign responder */}
            <div>
              <label htmlFor="dispatch-responder" className={labelClass}>
                Assign Responder
              </label>

              <select
                id="dispatch-responder"
                value={dispatchForm.assigned_user_id}
                onChange={(event) =>
                  setDispatchForm((current) => ({
                    ...current,
                    assigned_user_id: event.target.value,
                  }))
                }
                className={inputClass}
                disabled={optionsLoading || responders.length === 0}
              >
                <option value="">
                  {optionsLoading
                    ? "Loading responders..."
                    : responders.length === 0
                      ? "No responders available"
                      : "Unassigned"}
                </option>

                {responders.map((item) => {
                  const id = item.user_id ?? item.id;
                  if (id == null) return null;

                  const name =
                    item.name ||
                    item.full_name ||
                    item.username ||
                    item.email ||
                    `Responder ${id}`;

                  const role =
                    item.role_name ||
                    item.user_role ||
                    item.role?.name ||
                    "";

                  return (
                    <option key={id} value={id}>
                      {name}
                      {role ? ` (${role})` : ""}
                    </option>
                  );
                })}
              </select>

              {optionsLoading ? (
                <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                  Loading accident and responder options...
                </p>
              ) : responders.length === 0 ? (
                <p className="mt-1 text-xs text-amber-600 dark:text-amber-400">
                  No emergency responders found. Check the API response and
                  the role values returned by the backend.
                </p>
              ) : (
                <p className="mt-1 text-xs text-gray-500 dark:text-gray-400">
                  {responders.length} responder(s) available.
                </p>
              )}
            </div>

            {/* Initial status */}
            <div>
              <label htmlFor="dispatch-status" className={labelClass}>
                Initial Status
              </label>

              <select
                id="dispatch-status"
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

            {/* Operational notes */}
            <div>
              <label htmlFor="dispatch-notes" className={labelClass}>
                Operational Notes
              </label>

              <textarea
                id="dispatch-notes"
                rows={4}
                value={dispatchForm.notes}
                onChange={(event) =>
                  setDispatchForm((current) => ({
                    ...current,
                    notes: event.target.value,
                  }))
                }
                placeholder="Add dispatch instructions or details..."
                className={`${inputClass} resize-y`}
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
                    className="rounded-full border border-gray-300 px-3 py-1 text-xs text-gray-600 hover:bg-gray-50 dark:border-slate-600 dark:text-gray-300 dark:hover:bg-slate-800"
                  >
                    + {template}
                  </button>
                ))}
              </div>
            </div>

            {/* Form actions */}
            <div className="flex justify-end gap-2 border-t border-gray-200 pt-4 dark:border-slate-700">
              <button
                type="button"
                onClick={closeDispatch}
                className="rounded-lg border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50 dark:border-slate-600 dark:text-gray-200 dark:hover:bg-slate-800"
              >
                Cancel
              </button>

              <button
                type="submit"
                disabled={saving || optionsLoading}
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