async function autoLogin() {
	const jwt = localStorage.getItem("jwt");
	const result = document.getElementById("result");
	const balanceLabel = document.getElementById("balance");
	const balanceLabelTokens = document.getElementById("balance_tokences");

	if (!jwt) return;

	try {
		console.log("requesting by jwt", jwt);
		const res = await fetch("/me", {
			headers: {
				"Authorization": `Bearer ${jwt}`
			}
		});

		if (!res.ok) {
			throw new Error("JWT invalid or expired");
		}

		const data = await res.json();
		const address = data.address;

		result.textContent = "Welcome back: " + address + "\nUsing stored JWT.";

        await updateBlockchainData(address, jwt);

		// Load balances again (you can refactor to a function)
		// const provider = new ethers.providers.Web3Provider(window.ethereum);
		// const rawBalance = await provider.getBalance(address);
		// const ethBalance = ethers.utils.formatEther(rawBalance);
		// balanceLabel.textContent = parseFloat(ethBalance);

		// Get PIT balance from backend
		// const verifyRes = await fetch("/verify_signature", {
		// 	method: "POST",
		// 	headers: { "Content-Type": "application/json" },
		// 	body: JSON.stringify({ address, signature: "" }) // dummy signature to get balance
		// });

		// const balanceData = await verifyRes.json();
		// balanceLabelTokens.textContent = balanceData.PIT_balance;

		console.log("Auto-login completed:", address);

		// const balanceRes = await fetch("/balance", {
		// 	headers: { "Authorization": `Bearer ${jwt}` }
		// });
		// const balanceData = await balanceRes.json();
		// balanceLabelTokens.textContent = balanceData.PIT_balance;

	} catch (err) {
		console.log("Auto-login failed:", err.message);
		localStorage.removeItem("jwt");
	}
}

async function login() {
	const result = document.getElementById("result");
	const balanceLabel = document.getElementById("balance");
	const balanceLabelTokens = document.getElementById("balance_tokences");

	try {
		if (!window.ethereum) {
			result.textContent = "MetaMask is not installed!";
			return;
		}

		const provider = new ethers.providers.Web3Provider(window.ethereum);
		await provider.send("eth_requestAccounts", []);
		const signer = provider.getSigner();
		const address = await signer.getAddress();

		result.textContent = "Connected address: " + address + "\nRequesting nonce...";

		// Get ETH balance
		const rawBalance = await provider.getBalance(address);
		const ethBalance = ethers.utils.formatEther(rawBalance);
		balanceLabel.textContent = parseFloat(ethBalance);

		const nonceRes = await fetch("/get_nonce", {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify({ address })
		});

		console.log(nonceRes);

		if (!nonceRes.ok) {
			const err = await nonceRes.text();
			throw new Error("Failed to get nonce: " + err);
		}

		const { nonce } = await nonceRes.json();
		console.log(nonce)
		const signature = await signer.signMessage(nonce);

		console.log(signature)

		const verifyRes = await fetch("/verify_signature", {
			method: "POST",
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify({ address, signature })
		});

		if (!verifyRes.ok) {
			const err = await verifyRes.text();
			throw new Error("Failed to verify signature: " + err);
		}
		const data = await verifyRes.json();

		balanceLabelTokens.textContent = data.PIT_balance

		if (data.token) {
			localStorage.setItem("jwt", data.token);
			result.textContent = "Logged in as: " + data.address + "\nJWT: " + data.token;
		} else {
			result.textContent = "Login failed.";
		}

	} catch (err) {
		console.error(err);
		result.textContent = "Error: " + err.message;
		balanceLabel.textContent = "-";
		balanceLabelTokens.textContent = "-"
	}
}

async function updateBlockchainData(address, jwt) {
	const provider = new ethers.providers.Web3Provider(window.ethereum);

	// Get ETH balance
	const rawBalance = await provider.getBalance(address);
	const ethBalance = ethers.utils.formatEther(rawBalance);
	document.getElementById("balance").textContent = parseFloat(ethBalance);

	// Get PIT token balance via backend
	const res = await fetch("/balance", {
		headers: {
			"Authorization": `Bearer ${jwt}`
		}
	});

    console.log(res);

	if (!res.ok) {
		throw new Error("Failed to fetch PIT balance");
	}

	const data = await res.json();
	document.getElementById("balance_tokences").textContent = data.PIT_balance;

    const runsTable = document.querySelector("#runs-table tbody");
    try {
        const res = await fetch("/runs", {
            headers: { "Authorization": `Bearer ${jwt}` }
        });

        if (!res.ok) {
            throw new Error("Failed to fetch runs");
        }

        const { runs } = await res.json();
        runsTable.innerHTML = runs.length ? "" : `<tr><td colspan="4">No runs found</td></tr>`;

        runs.forEach((run, i) => {
            const tr = document.createElement("tr");

            // Optionally convert status enum integer to human-readable string
            const statusMap = ["Requested", "Completed", "Cancelled", "Refunded"];
            const statusText = statusMap[run.status] || `Status #${run.status}`;

            tr.innerHTML = `
                <td>${i + 1}</td>
                <td><a href="${run.inputDataLink}" target="_blank">${run.inputDataHash}</a></td>
                <td><a href="${run.outputDataLink}" target="_blank">${run.outputDataHash}</a></td>
                <td>${run.randomState}</td>
                <td>${statusText}</td>
            `;
            runsTable.appendChild(tr);
        });

    } catch (err) {
        console.error("Failed to load runs:", err);
        runsTable.innerHTML = `<tr><td colspan="4">Error loading runs</td></tr>`;
    }
}

async function buyTokens () {
    if (typeof window.ethereum === "undefined") {
        alert("Please install MetaMask first 😊");
        return;
    }

    const ethAmountInput = document.getElementById("buy-eth-amount");
    const statusEl = document.getElementById("buy-status");
    statusEl.textContent = "";

    const ethAmount = ethAmountInput.value;

    if (!ethAmount || isNaN(ethAmount) || parseFloat(ethAmount) <= 0) {
        statusEl.textContent = "Please enter a valid ETH amount.";
        return;
    }

    try {
        const provider = new ethers.providers.Web3Provider(window.ethereum);
        await provider.send("eth_requestAccounts", []);
        const signer = provider.getSigner();

        const tx = await signer.sendTransaction({
            to: contractAddress,
            value: ethers.utils.parseEther(ethAmount)
        });

        statusEl.textContent = "Transaction sent…";
        await tx.wait();
        statusEl.textContent = "Tokens purchased!";

    } catch (err) {
        console.error(err);
        statusEl.textContent = "Transaction failed.";
    }
}

function setCatalogStatus(txt, loading = false) {
    const s = document.getElementById("catalog-status");
    s.textContent = txt;
    s.style.opacity = loading ? "0.7" : "1";
}

async function loadCatalog() {
    try {
        setCatalogStatus("Loading catalog…", true);
        const res = await fetch("/ai/catalog");
        const jobs = await res.json();
        const tbody = document.querySelector("#catalog tbody");
        tbody.innerHTML = "";
        jobs.forEach(job => {
        const tr = document.createElement("tr");
        tr.innerHTML = `
            <td>${job.name}</td>
            <td>${job.description}</td>
            <td>${job.price}</td>
            <td><input type="file" data-job="${job.id}"></td>
            <td><button data-job="${job.id}" data-price="${job.price}">Buy & Run</button></td>
        `;
        tbody.appendChild(tr);
        });
        setCatalogStatus("");
    } catch (e) {
        console.error(e);
        setCatalogStatus("Failed to load catalog");
    }
}

document.getElementById("catalog").addEventListener("click", async ev => {
    if (ev.target.tagName !== "BUTTON") return;
    const jobId = ev.target.dataset.job;
    const jobPrice = ev.target.dataset.price;
    const fileInput = document.querySelector(`input[type=file][data-job='${jobId}']`);
    if (!fileInput.files.length) return alert("Choose a file first");

    const jwt = localStorage.getItem("jwt");
    if (!jwt) return alert("Login first");

    const provider = new ethers.providers.Web3Provider(window.ethereum);
    await provider.send("eth_requestAccounts", []);
    const signer = provider.getSigner();

    const erc20Abi = [
        "function approve(address spender, uint256 amount) public returns (bool)"
    ];

    const tokenContract = new ethers.Contract(contractAddress, erc20Abi, signer);

    console.log("Job price " + String(jobPrice));

    const tx = await tokenContract.approve(piAddress, ethers.utils.parseUnits(String(jobPrice), 18));
    await tx.wait();
    console.log("Approved successfully!");

    const form = new FormData();
    form.append("job_id", jobId);
    form.append("data", fileInput.files[0]);

    setCatalogStatus("Uploading input file…", true);
    const upload = await fetch("/ai/prepare_run", {
        method: "POST",
        headers: {
            "Authorization": `Bearer ${jwt}`
        },
        body: form
    }).then(r => r.json());

    const { inputDataLink, inputDataHash, randomState } = upload;
    setCatalogStatus("File uploaded to " + inputDataLink + " with hash " + inputDataHash , true);
});

async function pollRun(runId) {
    const resCell = document.getElementById("result");
    const int = setInterval(async () => {
        const r = await fetch("/ai/status/" + runId).then(r => r.json());
        if (r.status.startsWith("done")) {
        clearInterval(int);
        alert("Run complete! Result ready.");
        // optional: refresh /runs table
        const jwt = localStorage.getItem("jwt");
        if (jwt) {
            const provider = new ethers.providers.Web3Provider(window.ethereum);
            const addr = await provider.getSigner().getAddress();
            await updateBlockchainData(addr, jwt);
        }
        } else if (r.status.startsWith("error")) {
        clearInterval(int);
        alert("Run failed: " + r.status);
        }
    }, 5000);
}


document.getElementById("login-btn").addEventListener("click", login);
document.getElementById("buy-btn").addEventListener("click", buyTokens);
window.addEventListener("load", loadCatalog);
window.addEventListener("load", autoLogin);