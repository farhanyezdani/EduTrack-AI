import { configureStore } from "@reduxjs/toolkit";
import auth from "./authSlice";
import { api } from "./api";

export const store = configureStore({
  reducer: {
    auth,
    [api.reducerPath]: api.reducer,
  },
  middleware: (getDefault) => getDefault().concat(api.middleware),
});
