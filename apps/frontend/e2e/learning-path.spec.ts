import { expect, test, type APIRequestContext } from "@playwright/test";

async function post<T>(request: APIRequestContext, url: string, data: unknown): Promise<T> {
  const response = await request.post(url, { data });
  expect(response.ok(), `${response.status()} ${await response.text()}`).toBeTruthy();
  return response.json() as Promise<T>;
}

test("draft path is edited, published, advanced and accepts remediation", async ({ page, request }) => {
  const api = process.env.PLAYWRIGHT_API_URL ?? "http://localhost:8000/api/v1";
  const suffix = Date.now();
  const space = await post<{ id: string }>(request, `${api}/learning-spaces`, {
    title: `E2E Path ${suffix}`,
    description: "Изолированный сценарий учебного пути",
    color: "#5f7894",
    status: "active",
  });
  await post<{ id: string }>(request, `${api}/learning-spaces/${space.id}/goals`, {
    title: "Освоить направленный учебный маршрут",
    priority: 100,
    status: "active",
    expected_capabilities: [],
    completion_criteria: [],
  });
  const prerequisite = await post<{ id: string }>(request, `${api}/concepts`, {
    learning_space_id: space.id,
    title: `Prerequisite ${suffix}`,
    aliases: [],
  });
  const target = await post<{ id: string }>(request, `${api}/concepts`, {
    learning_space_id: space.id,
    title: `Target ${suffix}`,
    aliases: [],
  });
  await post(request, `${api}/concept-relations`, {
    source_concept_id: prerequisite.id,
    target_concept_id: target.id,
    relation_type: "prerequisite_of",
  });
  await post(request, `${api}/materials`, {
    learning_space_id: space.id,
    type: "article",
    title: `Target material ${suffix}`,
    status: "active",
    metadata: { concept_ids: [target.id] },
  });

  await page.goto(`/spaces/${space.id}`);
  await page.getByRole("button", { name: "Построить путь" }).click();
  await page.getByLabel(`Target ${suffix}`).check();
  await page.getByRole("button", { name: "Создать draft" }).click();
  await page.getByRole("link", { name: "Открыть путь" }).click();
  await expect(page).toHaveURL(new RegExp(`/spaces/${space.id}/paths/`));
  await expect(page.locator(".path-canvas")).toBeVisible();
  await expect(page.locator(".path-outline-node")).toHaveCount(2);

  await page.getByRole("button", { name: "Edit mode" }).click();
  await page.locator(".path-edit-toolbar").getByRole("button", { name: "Ресурс" }).click();
  await page.getByLabel("Тип").selectOption("practice");
  await page.getByLabel("Название").fill("Объяснить prerequisite своими словами");
  await page.getByRole("button", { name: "Прикрепить" }).click();
  await page.getByRole("button", { name: "Опубликовать" }).click();
  await expect(page.getByText(/active · version/)).toBeVisible();

  const weakPrerequisite = await post<{ id: string }>(request, `${api}/concepts`, {
    learning_space_id: space.id,
    title: `Remediation ${suffix}`,
    aliases: [],
  });
  await post(request, `${api}/concept-relations`, {
    source_concept_id: weakPrerequisite.id,
    target_concept_id: target.id,
    relation_type: "prerequisite_of",
  });

  const pathId = page.url().split("/").at(-1)!;
  const detailResponse = await request.get(`${api}/learning-paths/${pathId}`);
  expect(detailResponse.ok()).toBeTruthy();
  const detail = (await detailResponse.json()) as {
    path: { version: number };
    current_node: { id: string };
  };
  const policyResponse = await request.patch(
    `${api}/learning-paths/${pathId}/nodes/${detail.current_node.id}`,
    { data: { expected_version: detail.path.version, completion_policy: {} } },
  );
  expect(policyResponse.ok(), await policyResponse.text()).toBeTruthy();
  await page.reload();

  await page.getByRole("button", { name: "Завершить узел" }).click();
  await expect(page.locator(".path-flow-node.current")).toContainText(`Target ${suffix}`);
  await expect(page.locator(".suggestions-panel")).toContainText(`Remediation ${suffix}`);

  const beforeAccept = await page.locator(".version-panel article").count();
  await page.locator(".suggestions-panel").getByRole("button", { name: "Accept" }).click();
  await expect(page.locator(".path-outline-node")).toHaveCount(3);
  await expect(page.locator(".version-panel article")).toHaveCount(beforeAccept + 1);

  const todayResponse = await request.get(`${api}/today?available_minutes=90`);
  expect(todayResponse.ok()).toBeTruthy();
  const today = (await todayResponse.json()) as {
    primary_action: { source_type: string; title: string } | null;
    secondary_actions: { source_type: string; title: string }[];
  };
  expect([today.primary_action, ...today.secondary_actions].some(
    (action) => action?.source_type === "learning_path_node_resource",
  )).toBeTruthy();
});
