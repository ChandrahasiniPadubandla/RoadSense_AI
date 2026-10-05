import React, { useEffect, useState } from 'react';

import {
  Bell,
  Menu,
  User,
  X,
  Pencil,
  Save,
} from 'lucide-react';

import { useAuth } from '../context/AuthContext';
import { useTheme } from '../context/ThemeContext';


export default function Topbar({
  title,
  onMenuClick,
}) {
  const {
    user,
    updateProfile,
  } = useAuth();

  const {
    isDarkMode,
    toggleTheme,
  } = useTheme();


  // ==================================================
  // PROFILE STATE
  // ==================================================

  const [showProfile, setShowProfile] = useState(false);

  const [isEditing, setIsEditing] = useState(false);

  const [profileName, setProfileName] = useState('');
  const [profilePhone, setProfilePhone] = useState('');

  const [isSaving, setIsSaving] = useState(false);

  const [profileError, setProfileError] = useState('');
  const [profileSuccess, setProfileSuccess] = useState('');


  // ==================================================
  // UPDATE PROFILE FIELDS WHEN USER CHANGES
  // ==================================================

  useEffect(() => {
    if (!user) {
      setProfileName('');
      setProfilePhone('');
      return;
    }

    setProfileName(user.name || '');
    setProfilePhone(user.phone || '');
  }, [user]);


  // ==================================================
  // OPEN PROFILE
  // ==================================================

  function handleOpenProfile() {
    setProfileName(user?.name || '');
    setProfilePhone(user?.phone || '');

    setProfileError('');
    setProfileSuccess('');
    setIsEditing(false);

    setShowProfile(true);
  }


  // ==================================================
  // CLOSE PROFILE
  // ==================================================

  function handleCloseProfile() {
    if (isSaving) return;

    setShowProfile(false);
    setIsEditing(false);

    setProfileError('');
    setProfileSuccess('');
  }


  // ==================================================
  // START EDITING
  // ==================================================

  function handleEditProfile() {
    setProfileName(user?.name || '');
    setProfilePhone(user?.phone || '');

    setProfileError('');
    setProfileSuccess('');

    setIsEditing(true);
  }


  // ==================================================
  // SAVE PROFILE
  // ==================================================

  async function handleSaveProfile(event) {
    event.preventDefault();

    setProfileError('');
    setProfileSuccess('');

    const trimmedName = profileName.trim();
    const trimmedPhone = profilePhone.trim();

    // Name validation
    if (!trimmedName) {
      setProfileError('Name cannot be empty.');
      return;
    }

    setIsSaving(true);

    try {
      /*
       * This calls:
       *
       * PUT /auth/me
       *
       * in your FastAPI backend.
       */
      const updatedUser = await updateProfile({
        name: trimmedName,
        phone: trimmedPhone || null,
      });

      // Update displayed values
      setProfileName(updatedUser.name || '');
      setProfilePhone(updatedUser.phone || '');

      setIsEditing(false);

      setProfileSuccess(
        'Profile updated successfully.'
      );
    } catch (error) {
      console.error(
        'Failed to update profile:',
        error
      );

      const message =
        error?.response?.data?.detail ||
        'Failed to update profile. Please try again.';

      setProfileError(message);
    } finally {
      setIsSaving(false);
    }
  }


  // ==================================================
  // ROLE
  // ==================================================

  const roleKey =
    typeof user?.role === 'string'
      ? user.role.toUpperCase()
      : '';

  const ROLE_LABELS = {
    SUPER_ADMIN: 'Super Admin',
    TRAFFIC_AUTHORITY: 'Traffic Authority',
    EMERGENCY_RESPONSE: 'Emergency Response',
    VIEWER: 'Viewer',
  };

  const roleLabel =
    ROLE_LABELS[roleKey] ||
    user?.role ||
    'User';


  // ==================================================
  // ALERT PERMISSION
  // ==================================================

  /*
   * These are the roles that can access Alerts.
   *
   * Change this list only if your existing project
   * uses different permissions.
   */
  const ALERT_ROLES = [
    'SUPER_ADMIN',
    'TRAFFIC_AUTHORITY',
    'EMERGENCY_RESPONSE',
    'VIEWER',
  ];

  const canViewAlerts =
    ALERT_ROLES.includes(roleKey);


  // ==================================================
  // RENDER
  // ==================================================

  return (
    <>
      {/* ==================================================
          TOPBAR
      ================================================== */}

      <header
        className="
          h-16
          flex
          items-center
          justify-between
          px-4
          md:px-6
          border-b
          border-asphalt-700/30
          bg-white
          dark:bg-asphalt-900
          text-asphalt-900
          dark:text-white
        "
      >

        {/* ==================================================
            LEFT SIDE
        ================================================== */}

        <div className="flex items-center gap-3">

          {/* Menu button */}

          <button
            type="button"
            onClick={onMenuClick}
            className="
              p-2
              rounded-lg
              hover:bg-asphalt-100
              dark:hover:bg-asphalt-800
              transition
            "
            aria-label="Open menu"
            title="Menu"
          >
            <Menu size={22} />
          </button>


          {/* Page title */}

          <h1
            className="
              text-lg
              md:text-xl
              font-semibold
              truncate
            "
          >
            {title}
          </h1>

        </div>


        {/* ==================================================
            RIGHT SIDE
        ================================================== */}

        <div className="flex items-center gap-2 md:gap-4">

          {/* ==================================================
              THEME BUTTON
          ================================================== */}

          <button
            type="button"
            onClick={toggleTheme}
            className="
              p-2
              rounded-lg
              hover:bg-asphalt-100
              dark:hover:bg-asphalt-800
              transition
            "
            aria-label="Toggle theme"
            title={
              isDarkMode
                ? 'Switch to light mode'
                : 'Switch to dark mode'
            }
          >
            {isDarkMode ? '☀️' : '🌙'}
          </button>


          {/* ==================================================
              ALERTS
          ================================================== */}

          {canViewAlerts && (
            <a
              href="/alerts"
              className="
                p-2
                rounded-lg
                hover:bg-asphalt-100
                dark:hover:bg-asphalt-800
                transition
              "
              aria-label="Alerts"
              title="Alerts"
            >
              <Bell size={21} />
            </a>
          )}


          {/* ==================================================
              USER PROFILE BUTTON
          ================================================== */}

          <button
            type="button"
            onClick={handleOpenProfile}
            className="
              flex
              items-center
              gap-2
              px-2
              py-1.5
              rounded-lg
              hover:bg-asphalt-100
              dark:hover:bg-asphalt-800
              transition
              text-left
            "
            aria-label="Open profile"
            title="My Profile"
          >

            {/* Avatar */}

            <div
              className="
                w-9
                h-9
                rounded-full
                flex
                items-center
                justify-center
                bg-signal-blue
                text-white
                flex-shrink-0
              "
            >
              <User size={18} />
            </div>


            {/* Name + role */}

            <div className="hidden sm:block">

              <div
                className="
                  text-sm
                  font-semibold
                  leading-tight
                "
              >
                {user?.name || 'User'}
              </div>

              <div
                className="
                  text-xs
                  text-asphalt-500
                  dark:text-asphalt-300
                "
              >
                {roleLabel}
              </div>

            </div>

          </button>

        </div>

      </header>


      {/* ==================================================
          PROFILE MODAL
      ================================================== */}

      {showProfile && (
        <div
          className="
            fixed
            inset-0
            z-50
            flex
            items-center
            justify-center
            p-4
            bg-black/50
          "
          onMouseDown={(event) => {
            if (
              event.target === event.currentTarget &&
              !isSaving
            ) {
              handleCloseProfile();
            }
          }}
        >

          {/* ==================================================
              PROFILE CARD
          ================================================== */}

          <div
            className="
              w-full
              max-w-md
              rounded-2xl
              bg-white
              dark:bg-asphalt-900
              text-asphalt-900
              dark:text-white
              shadow-2xl
              border
              border-asphalt-200
              dark:border-asphalt-700
              overflow-hidden
            "
          >

            {/* ==================================================
                MODAL HEADER
            ================================================== */}

            <div
              className="
                flex
                items-center
                justify-between
                px-5
                py-4
                border-b
                border-asphalt-200
                dark:border-asphalt-700
              "
            >

              <div>

                <h2
                  className="
                    text-lg
                    font-semibold
                  "
                >
                  My Profile
                </h2>

                <p
                  className="
                    text-xs
                    text-asphalt-500
                    dark:text-asphalt-300
                    mt-0.5
                  "
                >
                  View and manage your account details
                </p>

              </div>


              {/* Close button */}

              <button
                type="button"
                onClick={handleCloseProfile}
                disabled={isSaving}
                className="
                  p-2
                  rounded-lg
                  hover:bg-asphalt-100
                  dark:hover:bg-asphalt-800
                  transition
                "
                aria-label="Close profile"
                title="Close"
              >
                <X size={20} />
              </button>

            </div>


            {/* ==================================================
                PROFILE FORM
            ================================================== */}

            <form
              onSubmit={handleSaveProfile}
              className="p-5 space-y-4"
            >

              {/* ==================================================
                  NAME
              ================================================== */}

              <div>

                <label
                  className="
                    block
                    text-sm
                    font-medium
                    mb-1.5
                  "
                >
                  Name
                </label>


                {isEditing ? (

                  <input
                    type="text"
                    value={profileName}
                    onChange={(event) =>
                      setProfileName(
                        event.target.value
                      )
                    }
                    className="
                      w-full
                      px-3
                      py-2.5
                      rounded-lg
                      border
                      border-asphalt-300
                      dark:border-asphalt-600
                      bg-white
                      dark:bg-asphalt-800
                      text-asphalt-900
                      dark:text-white
                      outline-none
                      focus:ring-2
                      focus:ring-signal-blue
                    "
                    placeholder="Enter your name"
                    disabled={isSaving}
                  />

                ) : (

                  <div
                    className="
                      px-3
                      py-2.5
                      rounded-lg
                      bg-asphalt-100
                      dark:bg-asphalt-800
                    "
                  >
                    {user?.name || 'Not provided'}
                  </div>

                )}

              </div>


              {/* ==================================================
                  PHONE
              ================================================== */}

              <div>

                <label
                  className="
                    block
                    text-sm
                    font-medium
                    mb-1.5
                  "
                >
                  Phone Number
                </label>


                {isEditing ? (

                  <input
                    type="tel"
                    value={profilePhone}
                    onChange={(event) =>
                      setProfilePhone(
                        event.target.value
                      )
                    }
                    className="
                      w-full
                      px-3
                      py-2.5
                      rounded-lg
                      border
                      border-asphalt-300
                      dark:border-asphalt-600
                      bg-white
                      dark:bg-asphalt-800
                      text-asphalt-900
                      dark:text-white
                      outline-none
                      focus:ring-2
                      focus:ring-signal-blue
                    "
                    placeholder="Enter your phone number"
                    disabled={isSaving}
                  />

                ) : (

                  <div
                    className="
                      px-3
                      py-2.5
                      rounded-lg
                      bg-asphalt-100
                      dark:bg-asphalt-800
                    "
                  >
                    {user?.phone || 'Not provided'}
                  </div>

                )}

              </div>


              {/* ==================================================
                  EMAIL
              ================================================== */}

              <div>

                <label
                  className="
                    block
                    text-sm
                    font-medium
                    mb-1.5
                  "
                >
                  Email
                </label>


                <div
                  className="
                    px-3
                    py-2.5
                    rounded-lg
                    bg-asphalt-100
                    dark:bg-asphalt-800
                    text-asphalt-600
                    dark:text-asphalt-300
                  "
                >
                  {user?.email || 'Not provided'}
                </div>


                <p
                  className="
                    text-xs
                    text-asphalt-500
                    dark:text-asphalt-400
                    mt-1
                  "
                >
                  Email address cannot be changed here.
                </p>

              </div>


              {/* ==================================================
                  ROLE
              ================================================== */}

              <div>

                <label
                  className="
                    block
                    text-sm
                    font-medium
                    mb-1.5
                  "
                >
                  Role
                </label>


                <div
                  className="
                    px-3
                    py-2.5
                    rounded-lg
                    bg-asphalt-100
                    dark:bg-asphalt-800
                  "
                >
                  {roleLabel}
                </div>

              </div>


              {/* ==================================================
                  ERROR MESSAGE
              ================================================== */}

              {profileError && (
                <div
                  className="
                    rounded-lg
                    px-3
                    py-2.5
                    text-sm
                    bg-red-100
                    text-red-700
                    dark:bg-red-900/30
                    dark:text-red-300
                  "
                >
                  {profileError}
                </div>
              )}


              {/* ==================================================
                  SUCCESS MESSAGE
              ================================================== */}

              {profileSuccess && (
                <div
                  className="
                    rounded-lg
                    px-3
                    py-2.5
                    text-sm
                    bg-green-100
                    text-green-700
                    dark:bg-green-900/30
                    dark:text-green-300
                  "
                >
                  {profileSuccess}
                </div>
              )}


              {/* ==================================================
                  BUTTONS
              ================================================== */}

              <div
                className="
                  flex
                  justify-end
                  gap-2
                  pt-2
                "
              >

                {isEditing ? (

                  <>
                    {/* Cancel */}

                    <button
                      type="button"
                      onClick={() => {
                        setProfileName(
                          user?.name || ''
                        );

                        setProfilePhone(
                          user?.phone || ''
                        );

                        setProfileError('');
                        setProfileSuccess('');

                        setIsEditing(false);
                      }}
                      disabled={isSaving}
                      className="
                        px-4
                        py-2
                        rounded-lg
                        border
                        border-asphalt-300
                        dark:border-asphalt-600
                        hover:bg-asphalt-100
                        dark:hover:bg-asphalt-800
                        transition
                      "
                    >
                      Cancel
                    </button>


                    {/* Save */}

                    <button
                      type="submit"
                      disabled={isSaving}
                      className="
                        inline-flex
                        items-center
                        gap-2
                        px-4
                        py-2
                        rounded-lg
                        bg-signal-blue
                        text-white
                        hover:opacity-90
                        disabled:opacity-50
                        transition
                      "
                    >

                      <Save size={16} />

                      {isSaving
                        ? 'Saving...'
                        : 'Save Changes'}

                    </button>
                  </>

                ) : (

                  /* Edit Profile */

                  <button
                    type="button"
                    onClick={handleEditProfile}
                    className="
                      inline-flex
                      items-center
                      gap-2
                      px-4
                      py-2
                      rounded-lg
                      bg-signal-blue
                      text-white
                      hover:opacity-90
                      transition
                    "
                  >
                    <Pencil size={16} />
                    Edit Profile
                  </button>

                )}

              </div>

            </form>

          </div>

        </div>
      )}

    </>
  );
}