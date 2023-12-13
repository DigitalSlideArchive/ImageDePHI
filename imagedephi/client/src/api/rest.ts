
export async function getDirectoryInfo(path?:string) {
    const selectedPath= path ? path : '/';
    const response = await fetch(`${import.meta.env.VITE_APP_API_URL}/directory?directory=${selectedPath}` , {method: "GET", mode: 'cors'});
    return response.json().then((data) => { return data[0].directory_data; })

}
