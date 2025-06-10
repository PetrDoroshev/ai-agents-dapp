const PiContr = artifacts.require("PiContr");
const MyToken = artifacts.require("MyToken");

module.exports = async function (deployer) {
    const name = "PiCoin";
    const symbol = "PIC"
    const decimals = 18;

    await deployer.deploy(MyToken, name, symbol, decimals);

    const tokenInstance = await MyToken.deployed();
    const tokenPrice = web3.utils.toWei("10", "ether");


    await deployer.deploy(PiContr, tokenInstance.address, tokenPrice);
};