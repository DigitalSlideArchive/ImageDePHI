const basePath = import.meta.env.VITE_APP_API_URL
  ? import.meta.env.VITE_APP_API_URL
  : "";

export async function getDirectoryInfo(path?: string) {
  const selectedPath = path ? path : "/";
  const response = await fetch(
    `${basePath}/directory/?directory=${selectedPath}`,
    {
      method: "GET",
      mode: "cors",
    },
  );
  return response.json().then((data) => {
    return data[0].directory_data;
  });
}

export async function getRedactionPlan(
  path: string,
  limit?: number,
  offset?: number,
) {
  const response = await fetch(
    `${basePath}/redaction_plan?input_directory=${path}&limit=${limit}&offset=${offset}`,
    {
      method: "GET",
      mode: "cors",
    },
  );
  return response.json().then((data) => {
    return data;
  });
}

export async function redactImages(
  inputDirectory: string,
  outputDirectory: string,
) {
  const response = await fetch(
    `${basePath}/redact/?input_directory=${inputDirectory}&output_directory=${outputDirectory}`,
    {
      method: "POST",
      mode: "cors",
    },
  );
  return response;
}
