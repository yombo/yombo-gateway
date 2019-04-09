import DashboardSidebar from './DashboardSideBar.vue';
import DashboardSidebarItem from './DashboardSidebarItem.vue';

const DashboardSidebarStore = {
  showDashboardSidebar: false,
  dashboardsidebarLinks: [],
  isMinimized: false,
  displayDashboardSidebar(value) {
    this.showDashboardSidebar = value;
  },
  toggleMinimize() {
    document.body.classList.toggle('dashboard-sidebar-mini');
    // we simulate the window Resize so the charts will get updated in realtime.
    const simulateWindowResize = setInterval(() => {
      window.dispatchEvent(new Event('resize'));
    }, 180);

    // we stop the simulation of Window Resize after the animations are completed
    setTimeout(() => {
      clearInterval(simulateWindowResize);
    }, 1000);

    this.isMinimized = !this.isMinimized;
  }
};

const DashboardSidebarPlugin = {
  install(Vue, options) {
    if (options && options.dashboardsidebarLinks) {
      DashboardSidebarStore.dashboardsidebarLinks = options.dashboardsidebarLinks;
    }
    let app = new Vue({
      data: {
        dashboardsidebarStore: DashboardSidebarStore
      }
    });
    Vue.prototype.$dashboardsidebar = app.dashboardsidebarStore;
    Vue.component('dashboard-side-bar', DashboardSidebar);
    Vue.component('dashboard-sidebar-item', DashboardSidebarItem);
  }
};

export default DashboardSidebarPlugin;
