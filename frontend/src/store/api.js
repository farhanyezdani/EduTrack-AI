import { createApi, fetchBaseQuery } from "@reduxjs/toolkit/query/react";
import { loggedOut } from "./authSlice";

const baseQuery = fetchBaseQuery({
  baseUrl: "/api",
  prepareHeaders: (headers, { getState }) => {
    const token = getState().auth.token;
    if (token) headers.set("Authorization", `Bearer ${token}`);
    return headers;
  },
});

// log out on 401 (expired token)
const baseQueryWithLogout = async (args, api, extra) => {
  const result = await baseQuery(args, api, extra);
  if (result.error?.status === 401 && api.getState().auth.token) api.dispatch(loggedOut());
  return result;
};

export const api = createApi({
  reducerPath: "api",
  baseQuery: baseQueryWithLogout,
  tagTypes: ["Students", "Student", "Dashboard"],
  endpoints: (b) => ({
    login: b.mutation({ query: (body) => ({ url: "/auth/login", method: "POST", body }) }),
    register: b.mutation({ query: (body) => ({ url: "/auth/register", method: "POST", body }) }),

    getSummary: b.query({ query: () => "/dashboard/summary", providesTags: ["Dashboard"] }),

    getStudents: b.query({
      query: (params) => ({ url: "/students", params }),
      providesTags: ["Students"],
    }),
    getStudent: b.query({
      query: (id) => `/students/${id}`,
      providesTags: (r, e, id) => [{ type: "Student", id }],
    }),
    createStudent: b.mutation({
      query: (body) => ({ url: "/students", method: "POST", body }),
      invalidatesTags: ["Students", "Dashboard"],
    }),
    updateProfile: b.mutation({
      query: ({ id, ...body }) => ({ url: `/students/${id}`, method: "PUT", body }),
      invalidatesTags: (r, e, { id }) => ["Students", { type: "Student", id }],
    }),
    deleteStudent: b.mutation({
      query: (id) => ({ url: `/students/${id}`, method: "DELETE" }),
      invalidatesTags: ["Students", "Dashboard"],
    }),
    uploadCsv: b.mutation({
      query: (file) => {
        const form = new FormData();
        form.append("file", file);
        return { url: "/students/upload", method: "POST", body: form };
      },
      invalidatesTags: ["Students", "Dashboard"],
    }),
    addAssessment: b.mutation({
      query: ({ id, ...body }) => ({ url: `/students/${id}/assessments`, method: "POST", body }),
      invalidatesTags: (r, e, { id }) => ["Students", "Dashboard", { type: "Student", id }],
    }),
    getPlan: b.query({ query: ({ id }) => `/students/${id}/plan` }),
    addIntervention: b.mutation({
      query: ({ id, ...body }) => ({ url: `/students/${id}/interventions`, method: "POST", body }),
      invalidatesTags: (r, e, { id }) => ["Dashboard", { type: "Student", id }],
    }),
    updateIntervention: b.mutation({
      query: ({ id, iid, ...body }) => ({ url: `/students/${id}/interventions/${iid}`, method: "PATCH", body }),
      invalidatesTags: (r, e, { id }) => ["Dashboard", { type: "Student", id }],
    }),

    getMetrics: b.query({ query: () => "/model/metrics" }),
    predict: b.mutation({ query: (body) => ({ url: "/model/predict", method: "POST", body }) }),
  }),
});

export const {
  useLoginMutation, useRegisterMutation, useGetSummaryQuery, useGetStudentsQuery, useGetStudentQuery,
  useCreateStudentMutation, useUpdateProfileMutation, useDeleteStudentMutation, useUploadCsvMutation,
  useAddAssessmentMutation, useGetPlanQuery, useAddInterventionMutation, useUpdateInterventionMutation,
  useGetMetricsQuery, usePredictMutation,
} = api;
