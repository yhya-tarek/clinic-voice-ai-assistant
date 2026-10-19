# clinic_db_final.py

import psycopg2
from psycopg2.extras import RealDictCursor
from typing import Optional, List, Dict, Any
from datetime import date, time, timedelta, datetime
import os
from dotenv import load_dotenv

load_dotenv()

class ClinicDB:
    def __init__(self):
        self.db_params = {
            "host": os.getenv("DB_HOST", "localhost"),
            "port": os.getenv("DB_PORT", "5432"),
            "dbname": os.getenv("DB_NAME", "clinic_test_db"),
            "user": os.getenv("DB_USER", "postgres"),
            "password": os.getenv("DB_PASSWORD", "postgres")
        }

    def _connect(self):
        return psycopg2.connect(**self.db_params, cursor_factory=RealDictCursor)

    # =========================================================
    # Helper: Standardized Response
    # =========================================================
    def _resp(self, success: bool, message: str, data: dict | list | None = None):
        return {
            "success": success,
            "message": message,
            "data": data
        }

    # =========================================================
    # 1. Setup DB
    # =========================================================
    def setup_database(self):
        conn = self._connect()
        cur = conn.cursor()
        try:
            sql = """
            DROP TABLE IF EXISTS booking_appointment CASCADE;
            DROP TABLE IF EXISTS drs_worktime CASCADE;
            DROP TABLE IF EXISTS patients CASCADE;
            DROP TABLE IF EXISTS drs CASCADE;

            CREATE TABLE drs (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                specialty VARCHAR(100),
                phone VARCHAR(20),
                email VARCHAR(100) UNIQUE,
                is_active BOOLEAN DEFAULT TRUE
            );

            CREATE TABLE patients (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                phone_no VARCHAR(20) UNIQUE NOT NULL
            );

            CREATE TABLE drs_worktime (
                id SERIAL PRIMARY KEY,
                doctor_id INTEGER REFERENCES drs(id) ON DELETE CASCADE,
                day_of_week SMALLINT CHECK (day_of_week BETWEEN 0 AND 6),
                start_time TIME NOT NULL,
                end_time TIME NOT NULL,
                is_available BOOLEAN DEFAULT TRUE,
                UNIQUE (doctor_id, day_of_week, start_time)
            );

            CREATE TABLE booking_appointment (
                id SERIAL PRIMARY KEY,
                patient_id INTEGER REFERENCES patients(id) ON DELETE CASCADE,
                doctor_id INTEGER REFERENCES drs(id) ON DELETE CASCADE,
                appointment_date DATE NOT NULL,
                appointment_time TIME NOT NULL,
                status VARCHAR(20) DEFAULT 'scheduled',
                notes TEXT,
                UNIQUE (doctor_id, appointment_date, appointment_time)
            );
            """
            cur.execute(sql)
            conn.commit()
            return self._resp(True, "Database initialized successfully.")
        except Exception as e:
            conn.rollback()
            return self._resp(False, f"Setup error: {e}")
        finally:
            cur.close()
            conn.close()

    # =========================================================
    # 2. Add Doctor
    # =========================================================
    def add_doctor(self, name: str, specialty: str = None, phone: str = None, email: str = None):
        try:
            conn = self._connect()
            cur = conn.cursor()

            cur.execute("""
                INSERT INTO drs (name, specialty, phone, email)
                VALUES (%s, %s, %s, %s)
                RETURNING id
            """, (name, specialty, phone, email))

            doc_id = cur.fetchone()["id"]
            conn.commit()
            return self._resp(True, "Doctor added.", {"doctor_id": doc_id})
        except Exception as e:
            return self._resp(False, f"Doctor creation failed: {e}")
        finally:
            cur.close()
            conn.close()

    # =========================================================
    # 3. Add Worktime
    # =========================================================
    def add_worktime(self, doctor_id: int, day_of_week: int, start_time: time, end_time: time):
        try:
            conn = self._connect()
            cur = conn.cursor()

            cur.execute("""
                INSERT INTO drs_worktime (doctor_id, day_of_week, start_time, end_time)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (doctor_id, day_of_week, start_time)
                DO UPDATE SET end_time = EXCLUDED.end_time
                RETURNING id
            """, (doctor_id, day_of_week, start_time, end_time))

            row = cur.fetchone()
            conn.commit()
            return self._resp(True, "Worktime added/updated.", {"worktime_id": row["id"]})
        except Exception as e:
            return self._resp(False, f"Worktime error: {e}")
        finally:
            cur.close()
            conn.close()

    # =========================================================
    # 4. Get / Create Patient
    # =========================================================
    def get_or_create_patient(self, phone_no: str, name: str | None):
        try:
            conn = self._connect()
            cur = conn.cursor()

            cur.execute("SELECT id FROM patients WHERE phone_no = %s", (phone_no,))
            row = cur.fetchone()

            if row:
                # if name:
                #     cur.execute("UPDATE patients SET name = %s WHERE id = %s", (name, row["id"]))
                #     conn.commit()
                return self._resp(True, "Patient loaded.", {"patient_id": row["id"]})

            # create new patient
            # name = name or f"Patient_{phone_no[-4:]}"
            cur.execute("""
                INSERT INTO patients (name, phone_no)
                VALUES (%s, %s)
                RETURNING id
            """, (name, phone_no))

            new_id = cur.fetchone()["id"]
            conn.commit()
            return self._resp(True, "New patient created.", {"patient_id": new_id})

        except Exception as e:
            return self._resp(False, f"Patient error: {e}")
        finally:
            cur.close()
            conn.close()

    # =========================================================
    # 5. Book Appointment
    # =========================================================
    def book_appointment(self, phone_no: int, doctor_id: int, appointment_date: date, appointment_time: time, name: str = None, notes: str = None):
        
        patient_res = self.get_or_create_patient(phone_no, name)
        if not patient_res["success"]:
            return patient_res
        
        patient_id = patient_res["data"]["patient_id"]

        try:
            conn = self._connect()
            cur = conn.cursor()

            cur.execute("""
                INSERT INTO booking_appointment (patient_id, doctor_id, appointment_date, appointment_time, notes)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (doctor_id, appointment_date, appointment_time) DO NOTHING
                RETURNING id
            """, (patient_id, doctor_id, appointment_date, appointment_time, notes or ""))

            row = cur.fetchone()

            if row:
                conn.commit()
                return self._resp(
                    True,
                    "Appointment booked successfully.",
                    {"appointment_id": row["id"], "doctor_id": doctor_id}
                )

            return self._resp(False, "Slot already booked.")

        except Exception as e:
            return self._resp(False, f"Booking error: {e}")
        finally:
            cur.close()
            conn.close()

    # =========================================================
    # 6. Upcoming Appointments
    # =========================================================
    def my_appointments(self, phone_no: str):
        try:
            conn = self._connect()
            cur = conn.cursor()

            cur.execute("""
                SELECT 
                    b.id,
                    b.appointment_date,
                    b.appointment_time,
                    b.status,
                    b.notes,
                    d.name AS doctor_name,
                    d.id AS doctor_id,
                    d.specialty
                FROM booking_appointment b
                JOIN patients p ON b.patient_id = p.id
                JOIN drs d ON b.doctor_id = d.id
                WHERE p.phone_no = %s
                AND (b.appointment_date > CURRENT_DATE
                    OR (b.appointment_date = CURRENT_DATE AND b.appointment_time >= CURRENT_TIME))
                AND b.status NOT IN ('cancelled', 'no-show')
                ORDER BY b.appointment_date, b.appointment_time
            """, (phone_no,))

            rows = cur.fetchall()

            formatted = [{
                "appointment_id": r["id"],
                "date": str(r["appointment_date"]),
                "time": r["appointment_time"].strftime("%H:%M"),
                "doctor_id": r["doctor_id"],
                "doctor": r["doctor_name"],
                "specialty": r["specialty"] or "General",
                "status": r["status"],
                "notes": r["notes"]
            } for r in rows]

            if not formatted:
                return self._resp(True, "No upcoming appointments.", [])

            return self._resp(True, "Appointments loaded.", formatted)

        except Exception as e:
            return self._resp(False, f"Appointment lookup error: {e}")
        finally:
            cur.close()
            conn.close()

    # =========================================================
    # 7. Update Appointment
    # =========================================================
    def update_appointment(self, appointment_id: int, phone_no: str, new_date=None, new_time=None, new_doctor_id:int=None, new_status=None, new_notes=None):

        try:
            conn = self._connect()
            cur = conn.cursor()

            sets = []
            params = []

            if new_date:
                sets.append("appointment_date = %s")
                params.append(date.fromisoformat(new_date))

            if new_time:
                sets.append("appointment_time = %s")
                params.append(time.fromisoformat(new_time))

            if new_doctor_id:
                sets.append("doctor_id = %s")
                params.append(new_doctor_id)

            if new_status:
                sets.append("status = %s")
                params.append(new_status)

            if new_notes:
                sets.append("notes = %s")
                params.append(new_notes)

            if not sets:
                return self._resp(False, "Nothing to update.")

            sql = f"""
                UPDATE booking_appointment
                SET {', '.join(sets)}
                WHERE id = %s
                AND patient_id = (SELECT id FROM patients WHERE phone_no = %s)
                RETURNING id, doctor_id, status
            """

            params.extend([appointment_id, phone_no])

            cur.execute(sql, params)
            row = cur.fetchone()

            if not row:
                return self._resp(False, "Appointment not found or unauthorized.")

            conn.commit()

            return self._resp(
                True,
                "Appointment updated.",
                {"appointment_id": row["id"], "doctor_id": row["doctor_id"], "status": row["status"]}
            )

        except Exception as e:
            return self._resp(False, f"Update error: {e}")
        finally:
            cur.close()
            conn.close()


    def _normalize_date(self, date_str: str) -> str:
        """Accepts formats like DD/MM/YYYY or DD-MM-YYYY and returns YYYY-MM-DD."""
        from datetime import datetime
        for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
            try:
                return datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
            except ValueError:
                pass
        raise ValueError(f"Invalid date format: {date_str}. Use YYYY-MM-DD or DD/MM/YYYY.")

    # =========================================================
    # 8. Specialty Availability
    # =========================================================
    def get_specialty_availability(self, specialty: str, days_ahead: int = 7, slot_duration: int = 30, date: str = None):
        try:
            conn = self._connect()
            cur = conn.cursor()

            # -----------------------------
            # If date provided → normalize it
            # -----------------------------
            if date:
                from datetime import datetime
                # Normalize input date to YYYY-MM-DD
                for fmt in ("%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d"):
                    try:
                        normalized_date = datetime.strptime(date, fmt).strftime("%Y-%m-%d")
                        break
                    except ValueError:
                        pass
                else:
                    return self._resp(False, f"Invalid date format: {date}")

                # Only ONE date
                date_sql = "SELECT CAST(%s AS DATE) AS dt"
                date_params = [normalized_date]

            else:
                # Generate multiple dates
                date_sql = """
                    SELECT generate_series(
                        current_date,
                        current_date + interval '1 day' * %s,
                        '1 day'
                    ) AS dt
                """
                date_params = [days_ahead]

            # -----------------------------
            # SQL Query (SAFE VERSION)
            # -----------------------------
            sql = f"""
            WITH dates AS (
                {date_sql}
            ),
            slots AS (
                SELECT
                    d.id AS doctor_id,
                    d.name AS doctor_name,
                    dt,
                    w.start_time,
                    w.end_time
                FROM dates
                JOIN drs d
                    ON LOWER(d.specialty) = LOWER(%s)
                    AND d.is_active
                JOIN drs_worktime w
                    ON w.doctor_id = d.id
                    AND EXTRACT(DOW FROM dt) = w.day_of_week
            ),
            raw_times AS (
                SELECT
                    s.doctor_id,
                    s.doctor_name,
                    s.dt,
                    to_char(gs.ser::time, 'HH24:MI') AS time
                FROM slots s
                JOIN LATERAL (
                    SELECT gs.ser
                    FROM generate_series(
                        s.dt + s.start_time,
                        s.dt + s.end_time - interval '%s minutes',
                        interval '%s minutes'
                    ) gs(ser)
                ) gs ON TRUE
                LEFT JOIN booking_appointment b
                    ON b.doctor_id = s.doctor_id
                    AND b.appointment_date = s.dt
                    AND b.appointment_time = gs.ser::time
                WHERE b.id IS NULL
            )
            SELECT
                doctor_id,
                doctor_name,
                json_agg(
                    json_build_object(
                        'date', to_char(dt, 'YYYY-MM-DD'),
                        'times', times
                    )
                ) AS available_slots
            FROM (
                SELECT
                    doctor_id,
                    doctor_name,
                    dt,
                    json_agg(time ORDER BY time) AS times
                FROM raw_times
                GROUP BY doctor_id, doctor_name, dt
                ORDER BY dt
            ) grouped
            GROUP BY doctor_id, doctor_name;
            """

            params = date_params + [specialty, slot_duration, slot_duration]

            cur.execute(sql, params)
            rows = cur.fetchall()

            # -----------------------------
            # FORMAT INTO "from X to Y"
            # -----------------------------
            formatted_output = []

            for r in rows:
                doctor_data = {
                    "doctor_id": r["doctor_id"],
                    "doctor_name": r["doctor_name"],
                    "available_slots": []
                }

                for slot in r["available_slots"]:
                    date = slot["date"]
                    times = slot["times"]

                    if times:
                        start = times[0]
                        end = times[-1]
                        formatted_line = f"{date}: from {start} to {end}"
                    else:
                        formatted_line = f"{date}: no available time"

                    doctor_data["available_slots"].append(formatted_line)

                formatted_output.append(doctor_data)

            return self._resp(True, "Availability loaded.", formatted_output)

        except Exception as e:
            return self._resp(False, f"Availability error: {e}")
        finally:
            cur.close()
            conn.close()

    # =========================================================
    # 9. Get All Patients
    # =========================================================
    def get_all_patients(self):
        try:
            conn = self._connect()
            cur = conn.cursor()

            cur.execute("""
                SELECT id, name, phone_no
                FROM patients
                ORDER BY id DESC
            """)

            rows = cur.fetchall()
            return self._resp(True, "Patients loaded.", rows)

        except Exception as e:
            return self._resp(False, f"Patients query error: {e}")
        finally:
            cur.close()
            conn.close()

    # =========================================================
    # 10. Get All Appointments
    # =========================================================
    def get_all_appointments(self):
        try:
            conn = self._connect()
            cur = conn.cursor()

            cur.execute("""
                SELECT
                    b.id,
                    p.name AS patient_name,
                    p.phone_no,
                    d.name AS doctor_name,
                    d.specialty,
                    b.appointment_date,
                    b.appointment_time,
                    b.status,
                    b.notes
                FROM booking_appointment b
                JOIN patients p ON b.patient_id = p.id
                JOIN drs d ON b.doctor_id = d.id
                ORDER BY b.appointment_date DESC, b.appointment_time DESC
            """)

            rows = cur.fetchall()

            formatted = [{
                "id": r["id"],
                "patient_name": r["patient_name"],
                "phone_no": r["phone_no"],
                "doctor_name": r["doctor_name"],
                "specialty": r["specialty"] or "General",
                "appointment_date": str(r["appointment_date"]),
                "appointment_time": r["appointment_time"].strftime("%H:%M"),
                "status": r["status"],
                "notes": r["notes"]
            } for r in rows]

            return self._resp(True, "Appointments loaded.", formatted)

        except Exception as e:
            return self._resp(False, f"Appointments query error: {e}")
        finally:
            cur.close()
            conn.close()

