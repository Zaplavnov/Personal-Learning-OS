import { expect, test } from "@playwright/test";

test("review completion changes the next action on Today", async ({ page, request }) => {
  const apiUrl = process.env.PLAYWRIGHT_API_URL ?? "http://localhost:8000";
  const conceptsResponse = await request.get(`${apiUrl}/api/v1/concepts`);
  expect(conceptsResponse.ok()).toBeTruthy();
  const concepts = (await conceptsResponse.json()) as { id: string; title: string }[];
  expect(concepts.length).toBeGreaterThan(0);
  const reviewResponse = await request.post(`${apiUrl}/api/v1/review-items`, {
    data: {
      concept_id: concepts[0].id,
      review_type: "explain",
      prompt: `E2E: объясни концепцию «${concepts[0].title}»`,
      expected_points: [],
      due_at: new Date(Date.now() - 60 * 60 * 1000).toISOString(),
    },
  });
  expect(reviewResponse.ok()).toBeTruthy();

  await page.goto("/today");
  const primaryTitle = page.getByTestId("today-primary-title");
  await expect(primaryTitle).toBeVisible();
  const initialAction = await primaryTitle.textContent();

  await page.getByTestId("start-primary-action").click();
  await expect(page).toHaveURL(/\/reviews/);
  await expect(page.getByTestId("review-answer")).toBeVisible();
  await page.getByTestId("review-answer").fill(
    "Собственный вектор сохраняет направление, потому что преобразование меняет его только в скалярное число раз.",
  );
  await page.getByTestId("review-result").selectOption("passed");
  await page.getByTestId("submit-review").click();

  await expect(page.getByTestId("review-completed")).toBeVisible();
  await page.getByTestId("return-today").click();
  await expect(page).toHaveURL(/\/today/);
  await expect(page.getByTestId("today-primary-title")).toBeVisible();
  await expect(page.getByTestId("today-primary-title")).not.toHaveText(initialAction ?? "");
});
