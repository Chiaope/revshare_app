import json
from flask import Flask, render_template, request
from dotenv import load_dotenv
from databricks import sql
import logging
import os

# from databricks.sdk import WorkspaceClient

question_ordered = [
    "status",
    "submitDate",
    "responder",
    "response_id",
    "score",
    "Who is the salesperson (Primary owner) completing this form?",
    "Is there a secondary owner assigned to this client profile? If yes, please specify.",
    "What is the client’s company registered name?",
    "What is the client's company registration number?",
    "What is the client’s company registered jurisdiction?",
    "How long has the client’s company been in operation?",
    "What is the client’s group structure (including parent and subsidiaries, if applicable)?",
    "Is the client publicly listed? If yes, where is it listed?",
    "What is the client’s primary regulator?",
    "What is the client’s associated license number?",
    "Does the client currently have any license applications in progress?",
    "Where are most of the client’s active end clients located?",
    "Is the client willing to provide financial information?",
    "What is the client’s primary business activity?",
    "Has the Sales team previously submitted this client’s data to Finalto for any revenue-sharing proposal or trade data analysis? If yes, when was the most recent submission?",
    "Do the client’s parent company or subsidiaries have any current or past relationships with Finalto? If yes, please specify the type of relationship.",
    "If yes, please provide the Finalto account number.",
    "Does the client currently have any revenue-sharing or profit-sharing arrangements with other liquidity providers?",
    "Profit-sharing ratio",
    "Settlement terms",
    "Any special conditions",
    "How is the client’s liquidity setup structured?",
    "If there are multiple liquidity providers, please list them.",
    "How would you best describe the client’s trade flow?",
    "Does the client operate an internal trading or risk management desk?",
    "Is the client able to provide end-client tagging (e.g., End-Tag or unique client ID)?",
    "Would the client be open to collaborating with us to optimize flow segmentation, where specific client groups or trading profiles are managed under different execution setups (e.g., differentiated pricing or accounts)?",
    "Is the client open to implementing a Minimum Account Holding (MAH) on the revenue-sharing account?",
    "What is the client’s fund structure?",
    "Is the client willing to provide trade data for analysis of trading behavior?",
    "Is the client willing to provide collateral to cover potential negative rebate balances under the revenue-sharing arrangement?",
    "What is the client’s preferred settlement structure?",
    "What is the client’s preferred profit-sharing settlement frequency?",
    "What NOP size is the client targeting?",
    "Is the client open to a profit holdback or reserve mechanism?",
    "Attachments",
]

default_status = "Pending"
available_status = ["Rejected", "Completed"]

internal_form_questions = [
    {
        "label": "Primary sales person rebate",
        "name_attr": "Primary sales person rebate",
        "input_type": "dropdown",
        "options": [
            "Negative rebate",
            "< 100k",
            "100k - 500k",
            "> 500k",
        ],
        "required": True,
    },
    {
        "label": "Secondary sales person rebate",
        "name_attr": "Secondary sales person rebate",
        "input_type": "dropdown",
        "options": [
            "Negative rebate",
            "< 100k",
            "100k - 500k",
            "> 500k",
        ],
        "required": True,
    },
    {
        "label": "C-board member history",
        "name_attr": "C-board member history",
        "input_type": "dropdown",
        "options": [
            "Any one of the C-board members has disciplinary record, bankruptcy record",
            "Any one of the C-board members is/was a board member of listed company",
            "CEO,COO both are/were a board member of listed company",
            "Others",
        ],
        "required": True,
    },
    {
        "label": "Client's business type according to license number",
        "name_attr": "Client's business type according to license number",
        "input_type": "dropdown",
        "options": [
            "Market Maker / Principal",
            "Hybrid (A-book + B-book)",
            "Pure STP / Agency",
            "Others",
        ],
        "required": True,
    },
    {
        "label": "If there is past relationship, what is the results",
        "name_attr": "If there is past relationship, what is the results",
        "input_type": "dropdown",
        "options": [
            "Yes- Revenue Share Deal [Manual checked and confirm the the risk taker has generated loss for Company]",
            "Yes- Revenue Share Deal [Manual checked and confirm the the risk taker has generated profit for Company] ",
        ],
        "required": False,
    },
]

load_dotenv(override=True)

log = logging.getLogger("werkzeug")
log.setLevel(logging.ERROR)

app = Flask(__name__)


score_mapping = {
    "Negative rebate": 0,
    "< 100k": 1,
    "100k - 500k": 3,
    "> 500k": 5,
    "Any one of the C-board members has disciplinary record, bankruptcy record": 0,
    "Any one of the C-board members is/was a board member of listed company": 3,
    "CEO,COO both are/were a board member of listed company": 5,
    "Others": 1,
    "Market Maker / Principal": 1,
    "Hybrid (A-book + B-book)": 3,
    "Pure STP / Agency": 5,
    "Yes- Revenue Share Deal [Manual checked and confirm the the risk taker has generated loss for Company]": 0,
    "Yes- Revenue Share Deal [Manual checked and confirm the the risk taker has generated profit for Company]": 5,
}


def run_databricks_query(sql_query, params=[], get_pandas=False):
    """
    Executes a SQL query on Databricks and returns the results.
    Make sure your environment variables are set!
    """
    # The context manager handles opening and closing the connection
    server_hostname = os.getenv("DATABRICKS_HOST")
    http_path = os.getenv("DATABRICKS_HTTP_PATH")
    access_token = os.getenv("MY_TOKEN")

    with sql.connect(
        server_hostname=server_hostname, http_path=http_path, access_token=access_token
    ) as connection:
        with connection.cursor() as cursor:

            cursor.execute(sql_query, parameters=params)
            if get_pandas:
                return cursor.fetchall_arrow().to_pandas()
            else:
                # 1. Grab the column names from the cursor description
                if not cursor.description:
                    print(f"No results returned for query: {sql_query}", flush=True)
                    return []
                columns = [column[0] for column in cursor.description]

                # 2. Fetch the raw data (which comes back as a list of tuples)
                rows = cursor.fetchall()
                if len(rows) == 0:
                    print(f"No results found for query: {sql_query}", flush=True)
                    return []

                # 3. Use list comprehension to zip columns and rows into dictionaries
                dict_results = [dict(zip(columns, row)) for row in rows]
                return dict_results


@app.route("/", methods=["GET"])
def index():
    query = "SELECT * from live_mart.riskmkt_apac.revshare_form where status = 'Pending' order by submitDate desc;"

    results = run_databricks_query(query)

    return render_template("index.html", data=results)

@app.errorhandler(500)
@app.errorhandler(404)
def handle_error(e):
    return render_template('error_page.html', message=str(e)), 500

@app.route("/internal-form", methods=["POST"])
def internal_form():
    # Grab the selected value from the dropdown using the <select> name attribute
    raw_selected_data = request.form.get("selected_data")
    if not raw_selected_data:
        return "<h1>Error</h1> <p>External response data not found.</p>"

    selected_data = json.loads(raw_selected_data)

    external_form_data = []
    for q in question_ordered:
        external_form_data.append({"question": q, "answer": selected_data[q]})

    if selected_data:
        selected_response_id = selected_data["response_id"]
        score = selected_data["score"]
        return render_template(
            "internal_form_page.html",
            selected_response_id=selected_response_id,
            score=score,
            internal_form_questions=internal_form_questions,
            external_form_data=external_form_data,
        )
    else:
        return "<h1>Error</h1> <p>No ID was selected.</p>"


@app.route("/review-form", methods=["POST"])
def review_form():
    data = dict(request.form)

    if not data:
        return "<h1>Error</h1> <p>No data submitted.</p>"
    score = int(data.get("score", 0))
    for key, value in data.items():
        if key in ["selected_response_id", "score"]:
            continue
        score += int(score_mapping.get(value, 0))

    data["score"] = score

    mapped_data = []

    for k, v in data.items():
        mapped_data.append({"question": k, "answer": v})

    return render_template(
        "review_page.html", form_data=mapped_data, available_status=available_status
    )


@app.route("/submit", methods=["POST"])
def submit():
    set_str_list = []
    param_list = []
    data = dict(request.form)
    print(f"Received form data: {data}", flush=True)

    if not data:
        return render_template("error_page.html", message="No data submitted.")

    score = int(data.get("score", 0))
    for key, value in data.items():
        if key in question_ordered + ["selected_status"]:
            continue
        set_str_list.append(f"`{key}` = ?")
        param_list.append(value)

    set_str = ", ".join(set_str_list)
    try:
        response_id = int(data["response_id"])
        status = data["selected_status"]
    except Exception as e:
        return render_template("error_page.html", message=f"Invalid input: {str(e)}")
    query = f"""
        UPDATE live_mart.riskmkt_apac.revshare_form
        SET 
            {set_str},
            score = ?,
            status = ?
        WHERE response_id = ?;
    """

    print(f"Query: {query}", flush=True)
    run_databricks_query(query, params=param_list + [score, status, response_id])

    return render_template("success_page.html")


if __name__ == "__main__":
    host = os.getenv("FLASK_RUN_HOST", "0.0.0.0")
    port = int(os.getenv("FLASK_RUN_PORT", 8000))

    app.run(debug=True, host=host, port=port, use_reloader=False)
    print(f"Flask app running on http://{host}:{port}")
