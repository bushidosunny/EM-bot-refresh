import streamlit as st



def main():
    st.title("My Streamlit App")
    st.write("Welcome to my app!")


    col1, col2 = st.columns(2)
    col1.write("Hi!")
    col2.write("Hi!")
    input = st.chat_input("Type a message...")
    st.markdown(f"You typed: {input}")




if __name__ == "__main__":
    main()