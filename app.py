import streamlit as st
import json
import pandas as pd
import time
import mysql.connector
from   mysql.connector import Error

import os

def load_css(filename):
    base_dir = os.path.dirname(__file__) 
    path = os.path.join(base_dir, filename)
    with open(path, 'r') as f:
        return f.read()

css = load_css('style.css')


# Set initial page configuration
st.set_page_config(
    page_title="Group Vote App",
    layout="wide", # Use wide layout for more space on results page
    initial_sidebar_state="expanded"
)

# Add a custom header
st.markdown("<h1 style='text-align: center; color: #007BFF;'> Group Vote App</h1>", unsafe_allow_html=True)

# Initialize session state for storing all polls
if 'polls' not in st.session_state:
    st.session_state.polls = []
    
# Initialize current_view and options_count if not present
if 'current_view' not in st.session_state:
    st.session_state.current_view = "dashboard"
if 'options_count' not in st.session_state:
    st.session_state.options_count = 2


def export_polls():
    # Converts current poll data to JSON and provides a download button
    if st.session_state.polls:
        json_data = json.dumps(st.session_state.polls, indent=4)
        st.download_button(
            label="⬇ Download All Poll Data (JSON)",
            data=json_data,
            file_name="group_polls_data.json",
            mime="application/json"
        )
    else:
        # Use st.info for a message inside the sidebar
        st.info("No data to export.")

def import_polls():
    # Allows user to upload a JSON file to load poll data
    uploaded_file = st.file_uploader(
        "⬆️ Upload Poll Data (JSON)", 
        type=["json"],
        help="Upload a file previously saved from this app."
    )
    
    if uploaded_file is not None:
        try:
            file_content = uploaded_file.getvalue().decode("utf-8")
            new_polls = json.loads(file_content)
            
            st.session_state.polls = new_polls
            
            # Use st.success/error which display nicely in the sidebar context
            st.success("Poll data successfully loaded!")
            st.rerun() 
            
        except json.JSONDecodeError:
            st.error("Error: Invalid JSON file format.")
        except Exception as e:
            st.error(f"An unexpected error occurred: {e}")


# VIEW FUNCTIONS

def create_poll_form():
    st.header("Create a New Poll")

    # LOGIC FOR ADDING OPTIONS (OUTSIDE the form)
    if st.button(" Add Another Option"): 
        st.session_state.options_count += 1
        st.rerun() 

    with st.form("new_poll_form", clear_on_submit=True):
        title = st.text_input("Poll Title/Question", key="new_poll_title")
        st.subheader("Options")
        
        option_inputs = {}
        for i in range(st.session_state.options_count):
            key_name = f"new_poll_option_{i}_{st.session_state.options_count}"
            option_inputs[f'option_{i}'] = st.text_input(f"Option {i+1}", key=key_name)
        
        st.checkbox("Vote Anonymously (Default)", value=True, disabled=True)
        
        submitted = st.form_submit_button("🚀 Launch Poll")

        if submitted and title and any(option.strip() for option in option_inputs.values()):
            options_dict = {opt.strip(): 0 for opt in option_inputs.values() if opt.strip()}
            
            new_poll = {
                "id": len(st.session_state.polls) + 1,
                "title": title,
                "options": options_dict,
                "status": "Open",
            }
            st.session_state.polls.append(new_poll)
            st.success(f"Poll '{title}' created!")
            st.session_state.options_count = 2 
            st.rerun()

def display_dashboard():
    st.subheader(" Welcome To Cloud Commanders Poll") 
    
    if not st.session_state.polls:
        st.info("No polls open right now. Click 'Create Poll' to get started!")
        return

    for poll in st.session_state.polls:
        # Use container to create the appealing card look
        with st.container(border=True): 
            st.subheader(poll["title"])
            col1, col2 = st.columns([1, 1])
            
            with col1:
                # Using CSS class for status color
                status_class = "status-open" if poll['status'] == 'Open' else "status-closed"
                st.markdown(f"Status: <span class='{status_class}'>{poll['status']}</span>", unsafe_allow_html=True)
            
            with col2:
                if st.button(" Vote Now / View Results", key=f"action_{poll['id']}"):
                    st.session_state.current_view = "vote"
                    st.session_state.selected_poll_id = poll["id"]
                    st.rerun()

def vote_on_poll(poll_id):
    poll = next((p for p in st.session_state.polls if p["id"] == poll_id), None)
    
    if not poll:
        st.error("Poll not found!")
        return

    st.header(poll["title"])
    
    selection = st.radio("Choose your option:", list(poll["options"].keys()))
    
    if st.button("✅ Submit Vote"):
        poll["options"][selection] += 1
        st.success(f"Vote counted for **{selection}**! Your vote is anonymous.")
        st.session_state.current_view = "results"
        st.rerun()

def display_results(poll_id):
    poll = next((p for p in st.session_state.polls if p["id"] == poll_id), None)
    
    if not poll: return

    st.header("📊 Live Results")
    st.subheader(poll["title"])
    
    # Use two columns for better layout: Chart on left, Metrics on right
    chart_col, metric_col = st.columns([3, 1]) 
    
    df = pd.DataFrame(
        list(poll["options"].items()), 
        columns=["Option", "Votes"]
    ).sort_values(by="Votes", ascending=False)
    
    with chart_col:
        st.bar_chart(df.set_index("Option"))

    with metric_col:
        total_votes = df["Votes"].sum()
        st.metric(label="Total Votes Cast", value=total_votes)
        st.metric(label="Status", value=poll["status"])

    # Real-time update logic
    if poll["status"] == "Open":
        st.caption("Results update automatically.")
        time.sleep(1) 
        st.rerun() 
        
    if st.button("⬅️ Back to Dashboard"): 
        st.session_state.current_view = "dashboard"
        st.rerun()

# Sidebar Navigation
st.sidebar.title("App Navigation")

if st.sidebar.button(" Home / Dashboard"):
    st.session_state.current_view = "dashboard"
    st.rerun()

if st.sidebar.button(" Create Poll"):
    st.session_state.current_view = "create"
    st.session_state.options_count = 2 
    st.rerun()

# --- Data Management Section ---
st.sidebar.markdown("---")
st.sidebar.subheader(" Data Management")

with st.sidebar:
    import_polls()
    st.markdown("---") 
    export_polls() 

#  Central Routing Logic
if st.session_state.current_view == "create":
    create_poll_form()
elif st.session_state.current_view == "vote":
    if 'selected_poll_id' in st.session_state:
        vote_on_poll(st.session_state.selected_poll_id)
    else:
        st.session_state.current_view = "dashboard"
elif st.session_state.current_view == "results":
    if 'selected_poll_id' in st.session_state:
        display_results(st.session_state.selected_poll_id)
    else:
        st.session_state.current_view = "dashboard"
else:
    display_dashboard()