import { createRouter, createWebHistory } from "vue-router";
import { useAuthStore } from "@/stores/auth";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", component: () => import("@/views/HomeView.vue") },
    { path: "/courses", component: () => import("@/views/CoursesView.vue") },
    {
      path: "/courses/:slug",
      component: () => import("@/views/CourseDetailView.vue"),
    },
    { path: "/wiki", component: () => import("@/views/WikiView.vue") },
    {
      path: "/wiki/:slug",
      component: () => import("@/views/WikiDetailView.vue"),
    },
    { path: "/projects", component: () => import("@/views/ProjectsView.vue") },
    {
      path: "/projects/submit",
      component: () => import("@/views/ProjectSubmitView.vue"),
      meta: { auth: true },
    },
    {
      path: "/projects/mine",
      component: () => import("@/views/MySubmissionsView.vue"),
      meta: { auth: true },
    },
    { path: "/skills", component: () => import("@/views/SkillsView.vue") },
    { path: "/auth", component: () => import("@/views/AuthView.vue") },
    {
      path: "/admin",
      component: () => import("@/views/AdminView.vue"),
      meta: { review: true },
    },
    { path: "/:pathMatch(.*)*", redirect: "/" },
  ],
});

router.beforeEach(async (to) => {
  const auth = useAuthStore();
  await auth.initialize();
  if (to.meta.auth && !auth.signedIn)
    return { path: "/auth", query: { returnTo: to.fullPath } };
  if (to.meta.review && !auth.canReview) return "/";
});

export default router;
