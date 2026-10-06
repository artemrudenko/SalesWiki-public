// Select the fixture or BFF client set without coupling page orchestration to transport details.

import {
  createBffCompanySearchClient, createBffDashboardClient, createBffDailyClient,
  createBffGraphClient, createBffGuidedAnswerClient, createBffImportClient,
  createBffReviewClient, createBffSessionClient, createBffUpdateClient,
  createFixtureCompanySearchClient, createFixtureDailyClient, createFixtureGraphClient,
  createFixtureGuidedAnswerClient, createFixtureImportClient, createFixtureReviewClient,
  createFixtureSessionClient, createFixtureUpdateClient,
} from "./graphClient";

export function createWorkbenchClients({ endpoint, accounts, adaptGraphView }) {
  if (endpoint) {
    return {
      graphClient: createBffGraphClient({ endpoint, adaptGraphView }),
      dailyClient: createBffDailyClient({ endpoint }), importClient: createBffImportClient({ endpoint }),
      reviewClient: createBffReviewClient({ endpoint }), updateClient: createBffUpdateClient({ endpoint }),
      sessionClient: createBffSessionClient({ endpoint }), companySearchClient: createBffCompanySearchClient({ endpoint }),
      guidedAnswerClient: createBffGuidedAnswerClient({ endpoint }), dashboardClient: createBffDashboardClient({ endpoint }),
    };
  }
  return {
    graphClient: createFixtureGraphClient({ accounts }), dailyClient: createFixtureDailyClient({ accounts }),
    importClient: createFixtureImportClient(), reviewClient: createFixtureReviewClient(),
    updateClient: createFixtureUpdateClient(), sessionClient: createFixtureSessionClient(),
    companySearchClient: createFixtureCompanySearchClient({ accounts }),
    guidedAnswerClient: createFixtureGuidedAnswerClient({ accounts }), dashboardClient: null,
  };
}
