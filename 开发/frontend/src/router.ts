import { createRouter, createWebHistory } from "vue-router";
import { useAuthStore } from "@/stores/auth";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", component: () => import("@/views/HomeView.vue") },
    { path: "/courses", component: () => import("@/views/CoursesView.vue") },
    {
      path: "/courses/:slug/:lessonSlug",
      component: () => import("@/views/CourseDetailView.vue"),
    },
    {
      path: "/courses/:slug",
      component: () => import("@/views/CourseDetailView.vue"),
      beforeEnter: to => to.hash.startsWith('#lesson-') && to.hash.length > 8
        ? { path: `/courses/${to.params.slug}/${to.hash.slice(8)}`, query: to.query, replace: true }
        : undefined,
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
    {
      path: "/skills",
      component: () => import("@/views/SkillsView.vue"),
      beforeEnter: to => to.query.create === "1"
        ? { path: "/skills/create", query: { ...(to.query.tab ? { tab: String(to.query.tab) } : {}) } }
        : undefined,
    },
    { path: "/skills/create", component: () => import("@/views/SkillCreateView.vue"), meta: { auth: true } },
    { path: "/skills/:slug/:version", component: () => import("@/views/SkillDetailView.vue") },
    { path: "/tools", component: () => import("@/views/ToolsView.vue") },
    { path: "/projects/:slug", component: () => import("@/views/ProjectsView.vue") },
    { path: "/profile", component: () => import("@/views/ProfileView.vue"), meta: { auth: true, account: true } },
    { path: "/profile/:section(info|security|projects|notifications)", component: () => import("@/views/ProfileView.vue"), meta: { auth: true, account: true } },
    { path: "/auth", redirect: to => ({ path: '/login', query: to.query }) },
    { path: "/login", component: () => import("@/views/AuthView.vue"), meta: { standalone: true } },
    { path: "/register", component: () => import("@/views/AuthView.vue"), meta: { standalone: true } },
    {
      path: "/admin",
      component: () => import("@/views/AdminView.vue"),
      meta: { auth: true, review: true },
    },
    { path: "/:pathMatch(.*)*", redirect: "/" },
  ],
});

router.beforeEach(async (to) => {
  const auth = useAuthStore();
  await auth.initialize();
  if (to.meta.auth && !auth.signedIn)
    return { path: "/login", query: { returnTo: to.fullPath } };
  if (to.meta.review && !auth.canReview) return "/";
});

export default router;
