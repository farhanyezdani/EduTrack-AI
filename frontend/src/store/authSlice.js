import { createSlice } from "@reduxjs/toolkit";

const saved = JSON.parse(localStorage.getItem("edutrack_auth") || "null");

const authSlice = createSlice({
  name: "auth",
  initialState: saved || { token: null, user: null },
  reducers: {
    loggedIn(state, action) {
      state.token = action.payload.access_token;
      state.user = action.payload.user;
      localStorage.setItem("edutrack_auth", JSON.stringify(state));
    },
    loggedOut(state) {
      state.token = null;
      state.user = null;
      localStorage.removeItem("edutrack_auth");
    },
  },
});

export const { loggedIn, loggedOut } = authSlice.actions;
export default authSlice.reducer;
