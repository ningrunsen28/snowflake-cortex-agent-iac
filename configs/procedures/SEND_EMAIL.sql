CREATE OR REPLACE PROCEDURE "SEND_EMAIL"("RECIPIENT_EMAIL" VARCHAR, "SUBJECT" VARCHAR, "BODY" VARCHAR)
RETURNS VARCHAR
LANGUAGE PYTHON
RUNTIME_VERSION = '3.12'
PACKAGES = ('snowflake-snowpark-python')
HANDLER = 'send_email'
EXECUTE AS OWNER
AS 'def send_email(session, recipient_email, subject, body):
    try:
        # Escape single quotes in the body
        escaped_body = body.replace("''", "''''")
        
        # Execute the system procedure call
        session.sql(f"""
            CALL SYSTEM$SEND_EMAIL(
                ''email_integration'',
                ''{recipient_email}'',
                ''{subject}'',
                ''{escaped_body}''
            )
        """).collect()
        
        return "Email sent successfully"
    except Exception as e:
        return f"Error sending email: {str(e)}"';