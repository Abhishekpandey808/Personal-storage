import React from "react";
import { Authenticator } from "@aws-amplify/ui-react";
import "@aws-amplify/ui-react/styles.css";
import FileManager from "./components/FileManager";
import "./App.css";

function App() {
  return (
    <Authenticator>
      {({ signOut, user }) => (
        <div className="app">
          <header className="app-header">
            <h1>☁️ Personal Cloud Storage</h1>
            <div className="header-right">
              <span className="user-email">{user?.attributes?.email || user?.username}</span>
              <button className="sign-out-btn" onClick={signOut}>
                Sign Out
              </button>
            </div>
          </header>
          <main className="app-main">
            <FileManager user={user} />
          </main>
        </div>
      )}
    </Authenticator>
  );
}

export default App;
