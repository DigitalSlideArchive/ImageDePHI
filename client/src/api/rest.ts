export async function getDirectoryInfo(path?:string) {
    const selectedPath= path ? path : '';
    const basePath = import.meta.env.VITE_APP_API_URL ? import.meta.env.VITE_APP_API_URL : '';
    const response = await fetch(`${basePath}/directory/${selectedPath}`, {method: "GET", mode: 'cors'});

    return response.json()

}
