### How to insert init mongo using .json files:

# Steps:
# 1: Identify container
# Use the right path
```bash
cd .\lessley-cd\     
```

# Print all containers
```bash
docker ps
```

# Look for mongo container
```bash
CONTAINER ID   IMAGE                         COMMAND                  CREATED          STATUS                    PORTS                                                                                          NAMES
d880d2dec8b7   mongo-express:latest          "/sbin/tini -- /dock…"   14 minutes ago   Up 14 minutes             0.0.0.0:8081->8081/tcp, [::]:8081->8081/tcp                                                    mongo_express

e617a141c059   mongo:8.0                     "docker-entrypoint.s…"   14 minutes ago   Up 14 minutes (healthy)   0.0.0.0:27017->27017/tcp, [::]:27017->27017/tcp                                                mongodb
```

You will need the `e617a141c059` container or use name `mongodb`.

# 2: Insert into mongodb container
```bash
docker cp ..\lessley-backend\Lessley.Personalization\resources\mccs.json mongodb:/tmp/mcc_list.json
```
# 3: Read from container and write to mongodb 
```bash
docker exec -it mongodb mongoimport --db lessley --collection mcc_list --file /tmp/mcc_list.json --jsonArray --username guest --password guest --authenticationDatabase admin
```

# 4: Repeat for deals and clubs
# stores
```bash
docker cp ..\lessley-backend\Lessley.Personalization\resources\stores.json mongodb:/tmp/store_list.json
```
```bash
docker exec -it mongodb mongoimport --db lessley --collection store_list --file /tmp/store_list.json --jsonArray --username guest --password guest --authenticationDatabase admin
```

# deals
```bash
docker cp ..\lessley-backend\Lessley.Personalization\resources\deals.json mongodb:/tmp/deal_list.json
```
```bash
docker exec -it mongodb mongoimport --db lessley --collection deal_list --file /tmp/deal_list.json --jsonArray --username guest --password guest --authenticationDatabase admin
```

# clubs
```bash
docker cp ..\lessley-backend\Lessley.Personalization\resources\clubs.json mongodb:/tmp/club_list.json
```
```bash
docker exec -it mongodb mongoimport --db lessley --collection club_list --file /tmp/club_list.json --jsonArray --username guest --password guest --authenticationDatabase admin
```