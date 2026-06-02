from app.database import execute_query


BAD_AGENT_PHONES = ("8762987365", "8762987322")


def cleanup():
    print("Removing junk delivery-agent test records...")
    rows = execute_query(
        "SELECT agent_id, full_name, phone FROM delivery_agents WHERE phone IN (%s, %s)",
        BAD_AGENT_PHONES,
    )
    if not rows:
        print("No junk test agents found.")
        return

    for row in rows:
        print(f"Deleting agent #{row['agent_id']}: {row['full_name']} ({row['phone']})")

    execute_query(
        "UPDATE bookings SET agent_id = NULL WHERE agent_id IN (SELECT agent_id FROM delivery_agents WHERE phone IN (%s, %s))",
        BAD_AGENT_PHONES,
        fetch=False,
    )
    execute_query(
        "DELETE FROM delivery_agents WHERE phone IN (%s, %s)",
        BAD_AGENT_PHONES,
        fetch=False,
    )
    print(f"Removed {len(rows)} junk test agent(s).")


if __name__ == "__main__":
    cleanup()
