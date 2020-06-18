/**
 * Stores Frontend settings.
 */

export const state = () => ({
  dashboardTablePaginationPosition: "both",
  dashboardTableTopPaginationSize: "sm",
  dashboardTableTopPaginationAlign: "right",
  dashboardTableBottomPaginationSize: "md",
  dashboardTableBottomPaginationAlign: "right",
  dashboardTableRowsPerPage: 20,
  dashboardPossibleRowsPerPage: [ 5, 10, 20, 50, 75, 100 ],
  lockScreenPassword: "",
  lockScreenPasswordHint: "",
  lockScreenLocked: false,
});

export const mutations = {
  set (state, values) {
    for (let property in values) {
      if (property in state) {
        state[property] = values[property];
      }
    }
  },
  screenLocked (state, value) {
    state['lockScreenLocked'] = value;
  },
  screenLockPassword (state, value) {
    console.log(`screenLockPassword: ${value}`);
    state['lockScreenPassword'] = value;
  },
  screenLockPasswordHint (state, value) {
    state['lockScreenPasswordHint'] = value;
  }
};
